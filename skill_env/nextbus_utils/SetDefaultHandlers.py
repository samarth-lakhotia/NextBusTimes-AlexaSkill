from NextBusAPIParser.Commands.RouteConfig import RouteConfig, RouteDoesNotExistException
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.serialize import DefaultSerializer
from ask_sdk_core.utils import is_intent_name, get_dialog_state, get_slot_value, get_slot
from ask_sdk_model import dialog_state, SlotConfirmationStatus, IntentConfirmationStatus, intent_confirmation_status
from ask_sdk_model.dialog import ElicitSlotDirective, ConfirmSlotDirective, DelegateDirective, ConfirmIntentDirective
from ask_sdk_model.slu.entityresolution import StatusCode
from nextbus_utils.Constants import R

SLOT_ROUTE_NUMBER = 'RouteNumber'
SLOT_STOP_NAME = 'StopName'
SET_DEFAULT_INTENT = "SetDefaultIntent"


class SetDefaultsHandlerStart(AbstractRequestHandler):
    '''
    Handler to start the conversation to set defaults
    '''

    def can_handle(self, handler_input):
        return is_intent_name(SET_DEFAULT_INTENT)(
            handler_input) and (get_dialog_state(handler_input) == dialog_state.DialogState.STARTED)

    def handle(self, handler_input):
        current_intent = handler_input.request_envelope.request.intent
        reprompt = "What is the bus number you looking for?"
        speech = "Can you provide me the bus number you are looking for?"
        return handler_input.response_builder.add_directive(
            ElicitSlotDirective(current_intent, SLOT_ROUTE_NUMBER)).speak(
            speech).ask(reprompt).response


class SetDefaultsHandlerInProgressRoute(AbstractRequestHandler):
    '''
    Handler to continue the conversation of setting defaults by first eliciting the bus number slot value
    '''

    def can_handle(self, handler_input):
        return is_intent_name(SET_DEFAULT_INTENT)(handler_input) and \
               get_dialog_state(handler_input) == dialog_state.DialogState.IN_PROGRESS and \
               get_slot_value(slot_name=SLOT_ROUTE_NUMBER, handler_input=handler_input) and \
               not get_slot_value(slot_name=SLOT_STOP_NAME, handler_input=handler_input)

    def handle(self, handler_input):
        obj_serializer = DefaultSerializer()
        current_intent = handler_input.request_envelope.request.intent

        reprompt = "what is the stop name you looking for?"
        speech = "Can you provide me the stop name you are looking for?"

        # Receive the slot that was stored when the user uttered the bus number
        bus_number = get_slot_value(slot_name=SLOT_ROUTE_NUMBER, handler_input=handler_input)
        current_intent.confirmation_status = IntentConfirmationStatus.NONE

        route = validate_route(bus_number)  # Says if the route is a vlid route of UMD or not
        if route:
            handler_input.attributes_manager.session_attributes[R.DEFAULT_ROUTE] = obj_serializer.serialize(
                {R.ROUTE_TITLE: route.route_title, R.ROUTE_TAG: route.route_tag})

            # Confirm the route just for the workflow
            current_intent.slots[SLOT_ROUTE_NUMBER].confirmation_status = SlotConfirmationStatus.CONFIRMED
            return handler_input.response_builder.add_directive(
                ElicitSlotDirective(current_intent, SLOT_STOP_NAME)).speak(
                speech).ask(reprompt).response
        else:
            # Set the slot to None so that if Delegation were to be used,
            # Alexa can know to ask for this slot automatically
            current_intent.slots[SLOT_ROUTE_NUMBER].value = None
            wrong_route_speech = "The bus number is incorrect. Please provide me with a valid bus number. What is the " \
                                 "bus number?"
            wrong_route_reprompt = "What is the bus number?"
            return handler_input.response_builder.add_directive(
                ElicitSlotDirective(current_intent, SLOT_ROUTE_NUMBER)).speak(
                wrong_route_speech).ask(wrong_route_reprompt).response


class SetDefaultsHandlerInProgressStopName(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name(SET_DEFAULT_INTENT)(handler_input) and \
               get_dialog_state(handler_input) == dialog_state.DialogState.IN_PROGRESS \
               and get_slot_value(slot_name=SLOT_ROUTE_NUMBER, handler_input=handler_input) and \
               get_slot_value(slot_name=SLOT_STOP_NAME, handler_input=handler_input) \
               and get_slot(handler_input, SLOT_STOP_NAME).confirmation_status == SlotConfirmationStatus.NONE

    def handle(self, handler_input):
        current_intent = handler_input.request_envelope.request.intent
        stop_val = get_slot(slot_name=SLOT_STOP_NAME, handler_input=handler_input)
        default_route = handler_input.attributes_manager.session_attributes.get(R.DEFAULT_ROUTE)
        if stop_val.resolutions:
            # Always true but just in case if later updates change
            matches = stop_val.resolutions.resolutions_per_authority
            if matches[0].status.code == StatusCode.ER_SUCCESS_MATCH:
                matched_stop = matches[0].values[0]
                route = RouteConfig.get_data_route_and_agency_tag(agency_tag="umd",
                                                                  route_tag=default_route[R.ROUTE_TAG])
                stop_id = matched_stop.value.id
                if route.has_stop(stop_id):
                    stop = route.get_stop_by_id(stop_id)
                else:
                    current_intent.slots[SLOT_STOP_NAME].value = None
                    return handler_input.response_builder.add_directive(
                        ElicitSlotDirective(current_intent, SLOT_STOP_NAME)).speak(
                        "The stop is not a stop for this route. Please try again with a stop name or stop number "
                        "that is in this route").ask("Provide a stop name or number").response
        #             else needed TODO:
        return handler_input.response_builder.add_directive(ConfirmSlotDirective(current_intent, SLOT_STOP_NAME)).speak(
            "The stop you have chosen is %s. Is that okay?" % stop.stop_title).ask(
            "Please confirm the stop %s" % stop.stop_title).response


class SetDefaultsHandlerInProgressStopNameConfirmed(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name(SET_DEFAULT_INTENT)(handler_input) and \
               get_dialog_state(handler_input) == dialog_state.DialogState.IN_PROGRESS \
               and get_slot_value(slot_name=SLOT_ROUTE_NUMBER, handler_input=handler_input) and \
               get_slot_value(slot_name=SLOT_STOP_NAME, handler_input=handler_input) \
               and get_slot(handler_input, SLOT_STOP_NAME).confirmation_status == SlotConfirmationStatus.CONFIRMED \
               and handler_input.request_envelope.request.intent.confirmation_status == IntentConfirmationStatus.NONE

    def handle(self, handler_input):
        current_intent = handler_input.request_envelope.request.intent
        obj_serializer = DefaultSerializer()
        stop_val = get_slot(slot_name=SLOT_STOP_NAME, handler_input=handler_input)
        default_route = handler_input.attributes_manager.session_attributes.get(R.DEFAULT_ROUTE)
        current_intent.confirmation_status = IntentConfirmationStatus.NONE
        matches = stop_val.resolutions.resolutions_per_authority
        # If the stop was matched with a valid name
        if matches[0].status.code == StatusCode.ER_SUCCESS_MATCH:
            matched_stop = matches[0].values[0]
            route = RouteConfig.get_data_route_and_agency_tag(agency_tag="umd",
                                                              route_tag=default_route[R.ROUTE_TAG])
            stop_id = matched_stop.value.id
            if route.has_stop(stop_id):
                stop = route.get_stop_by_id(stop_id)
                handler_input.attributes_manager.session_attributes[R.DEFAULT_STOP] = obj_serializer.serialize(
                    {R.STOP_ID: stop.stop_id, R.DIRECTION: stop.direction, R.STOP_TITLE: stop.stop_title})
            else:
                current_intent.slots[SLOT_STOP_NAME].value = None
                current_intent.slots[SLOT_STOP_NAME].confirmation_status = SlotConfirmationStatus.NONE
                return handler_input.response_builder.add_directive(
                    ElicitSlotDirective(current_intent, SLOT_STOP_NAME)).speak(
                    "The stop while confirming is not a stop for this route. Please try again with a stop name or stop number "
                    "that is in this route").ask("Provide a stop name or stop number").response
        return handler_input.response_builder.add_directive(ConfirmIntentDirective(current_intent)).speak(
            "I am setting these defaults. Is that okay?").response


class SetDefaultsHandlerInProgressStopNameDenied(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name(SET_DEFAULT_INTENT)(handler_input) and \
               get_dialog_state(handler_input) == dialog_state.DialogState.IN_PROGRESS \
               and get_slot_value(slot_name=SLOT_ROUTE_NUMBER, handler_input=handler_input) and \
               get_slot_value(slot_name=SLOT_STOP_NAME, handler_input=handler_input) \
               and get_slot(handler_input, SLOT_STOP_NAME).confirmation_status == SlotConfirmationStatus.DENIED

    def handle(self, handler_input):
        current_intent = handler_input.request_envelope.request.intent
        current_intent.slots[SLOT_STOP_NAME].value = None
        current_intent.slots[SLOT_STOP_NAME].confirmation_status = SlotConfirmationStatus.NONE

        return handler_input.response_builder.add_directive(
            ElicitSlotDirective(current_intent, SLOT_STOP_NAME)).speak(
            "Ok then. What is the name of the stop or stop number that you want to set default to?").ask(
            "Provide a stop name or number").response


class SetDefaultsHandlerInProgressIntentConfirmationConfirmed(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name(SET_DEFAULT_INTENT)(handler_input) and \
               get_dialog_state(handler_input) == dialog_state.DialogState.IN_PROGRESS \
               and get_slot_value(slot_name=SLOT_ROUTE_NUMBER, handler_input=handler_input) \
               and get_slot_value(slot_name=SLOT_STOP_NAME, handler_input=handler_input) \
               and handler_input.request_envelope.request.intent.confirmation_status == IntentConfirmationStatus.CONFIRMED

    def handle(self, handler_input):
        default_route = handler_input.attributes_manager.session_attributes.get(R.DEFAULT_ROUTE)
        default_stop = handler_input.attributes_manager.session_attributes.get(R.DEFAULT_STOP)
        handler_input.attributes_manager.persistent_attributes = handler_input.attributes_manager.session_attributes
        handler_input.attributes_manager.save_persistent_attributes()
        return handler_input.response_builder.speak(
            "Thank you! Your default route has been set to {} and the default stop to {}".format(
                default_route[R.ROUTE_TITLE],
                default_stop[R.STOP_TITLE])).response
        # current_intent = handler_input.request_envelope.request.intent
        # return handler_input.response_builder.add_directive(DelegateDirective(current_intent)).response


class SetDefaultsHandlerInProgressIntentConfirmationDenied(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name(SET_DEFAULT_INTENT)(handler_input) and \
               get_dialog_state(handler_input) == dialog_state.DialogState.IN_PROGRESS \
               and get_slot_value(slot_name=SLOT_ROUTE_NUMBER, handler_input=handler_input) \
               and get_slot_value(slot_name=SLOT_STOP_NAME, handler_input=handler_input) \
               and handler_input.request_envelope.request.intent.confirmation_status == IntentConfirmationStatus.DENIED

    def handle(self, handler_input):
        current_intent = handler_input.request_envelope.request.intent
        return handler_input.response_builder.speak(
            "Okay. To set defaults, tell me to ask umd dots to set").set_should_end_session(True).response


#             ElicitSlotDirective(current_intent, SLOT_ROUTE_NUMBER)).speak("In that case, can you provide me the Route Number").response

class SetDefaultsHandlerCompleted(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name(SET_DEFAULT_INTENT)(
            handler_input) and get_dialog_state(handler_input) == dialog_state.DialogState.COMPLETED

    def handle(self, handler_input):
        default_route = handler_input.attributes_manager.session_attributes.get(R.DEFAULT_ROUTE)
        default_stop = handler_input.attributes_manager.session_attributes.get(R.DEFAULT_STOP)
        handler_input.attributes_manager.persistent_attributes = handler_input.attributes_manager.session_attributes
        handler_input.attributes_manager.save_persistent_attributes()
        return handler_input.response_builder.speak(
            "Thank you! Your default route has been set to {} and the default stop to {}".format(
                default_route[R.ROUTE_TITLE],
                default_stop[R.STOP_TITLE])).response


def validate_route(route_input):
    try:
        route = RouteConfig.get_data_route_and_agency_tag(agency_tag="umd", route_tag=route_input)
        return route
    except RouteDoesNotExistException:
        return None
    except Exception as a:
        raise a
