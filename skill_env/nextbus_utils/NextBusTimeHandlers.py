from NextBusAPIParser.Commands.PredictionCommand import PredictionCommand
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.utils import is_request_type, is_intent_name, get_slot_value


class NextBusDefaultsHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type('IntentRequest')(handler_input) and is_intent_name('NextBusIntent')(
            handler_input) and not get_slot_value(handler_input, 'RouteNumber') and not get_slot_value(handler_input,
                                                                                                       'StopName')

    def handle(self, handler_input):
        route = handler_input.attributes_manager.persistent_attributes.get('default_route')
        stop = handler_input.attributes_manager.persistent_attributes.get('default_stop')
        prediction = PredictionCommand("umd").get_predictions_by_route_and_stop_id(
            route_tag=route.get('route_tag'), stop_id=stop.get('stop_id'))
        # handler_input.response_builder.speak("HERE HERE")
        if prediction[0].has_predictions:
            return handler_input.response_builder.speak(
                "The next {} bus comes at {} in {} minutes".format(route['route_title'], stop['stop_title'],
                                                           ",".join([x.minutes for x in prediction[0].directions[
                                                               stop['direction']]]))).response
        else:
            return handler_input.response_builder.speak("There are no predictions for this bus right now").response


class NextBusIntenthandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type('IntentRequest')(handler_input) and is_intent_name('NextBusIntent')(
            handler_input) and get_slot_value(handler_input, 'RouteNumber') and not get_slot_value(handler_input,
                                                                                                   'StopName')

    def handle(self, handler_input):
        pass