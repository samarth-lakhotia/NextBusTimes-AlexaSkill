from NextBusAPIParser.Containers.Agency import Agency
from ask_sdk.standard import StandardSkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.utils import is_request_type
from ask_sdk_model.dialog import DynamicEntitiesDirective
from ask_sdk_model.er.dynamic import update_behavior, entity, EntityValueAndSynonyms, EntityListItem
import pickle

from ask_sdk_model.ui import Card
from nextbus_utils.NextBusTimeHandlers import NextBusDefaultsHandler
from nextbus_utils.SetDefaultHandlers import SetDefaultsHandlerStart, SetDefaultsHandlerInProgressRoute, \
    SetDefaultsHandlerInProgressStopName, SetDefaultsHandlerInProgressStopNameDenied, \
    SetDefaultsHandlerInProgressStopNameConfirmed, SetDefaultsHandlerCompleted, \
    SetDefaultsHandlerInProgressIntentConfirmationDenied, SetDefaultsHandlerInProgressIntentConfirmationConfirmed

sb = StandardSkillBuilder(table_name="NextBus", auto_create_table=True)


class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        entities = bus_names_entity_creator()
        directive = DynamicEntitiesDirective(update_behavior=update_behavior.UpdateBehavior.REPLACE,
                                             types=[EntityListItem(name="BusRouteName", values=entities)])
        message = "Welcome to your personal Nextbus. To set defaults, say Alexa, ask my next bus to set defaults"
        return handler_input.response_builder.speak(message).add_directive(
            directive).set_should_end_session(False).response


def bus_names_entity_creator():
    agency = Agency("umd")
    routes = agency.route_list.route_list
    try:
        with open("/tmp/entities.pickle", "rb") as f:
            entities = pickle.load(f)
    except FileNotFoundError:
        entities = []
        with open("/tmp/entities.pickle", "wb") as f:
            for route in routes:
                synonyms = route.route_title.lower().split(maxsplit=1)
                synonyms = list(filter(None, synonyms))
                bus_values_and_synonyms = EntityValueAndSynonyms(value=route.route_title, synonyms=synonyms)
                bus_entity = entity.Entity(id=route.route_tag, name=bus_values_and_synonyms)
                entities.append(bus_entity)
            pickle.dump(entities, f)
    return entities


sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(SetDefaultsHandlerStart())
sb.add_request_handler(SetDefaultsHandlerInProgressRoute())
sb.add_request_handler(SetDefaultsHandlerInProgressStopName())
sb.add_request_handler(SetDefaultsHandlerInProgressStopNameDenied())
sb.add_request_handler(SetDefaultsHandlerInProgressStopNameConfirmed())
sb.add_request_handler(SetDefaultsHandlerInProgressIntentConfirmationDenied())
sb.add_request_handler(SetDefaultsHandlerInProgressIntentConfirmationConfirmed())
sb.add_request_handler(SetDefaultsHandlerCompleted())
sb.add_request_handler(NextBusDefaultsHandler())
lambda_handler = sb.lambda_handler()
