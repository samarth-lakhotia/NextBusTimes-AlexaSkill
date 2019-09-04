from NextBusAPIParser.Commands.RouteConfig import RouteConfig, RouteDoesNotExistException
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.serialize import DefaultSerializer
from ask_sdk_core.utils import is_intent_name, get_dialog_state, get_slot_value, get_slot
from ask_sdk_model import dialog_state, SlotConfirmationStatus
from ask_sdk_model.dialog import ElicitSlotDirective, ConfirmSlotDirective, DelegateDirective
from ask_sdk_model.slu.entityresolution import StatusCode


class SetDefaultsHandlerStart(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("SetDefaultIntent")(
            handler_input) and get_dialog_state(handler_input) == dialog_state.DialogState.STARTED

    def handle(self, handler_input):
        current_intent = handler_input.request_envelope.request.intent
        reprompt = "what is the bus number you looking for?"
        speech = "Can you provide me the bus number you are looking for?"
        return handler_input.response_builder.add_directive(ElicitSlotDirective(current_intent, 'RouteNumber')).speak(
            speech).response


class SetDefaultsHandlerInProgressRoute(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("SetDefaultIntent")(
            handler_input) and get_dialog_state(
            handler_input) == dialog_state.DialogState.IN_PROGRESS and get_slot_value(slot_name='RouteNumber',
                                                                                      handler_input=handler_input) and \
               not get_slot_value(slot_name='StopName', handler_input=handler_input)

    def handle(self, handler_input):
        obj_serializer = DefaultSerializer()
        current_intent = handler_input.request_envelope.request.intent
        reprompt = "what is the stop name you looking for?"
        speech = "Can you provide me the stop name you are looking for?"
        bus_number = get_slot_value(slot_name='RouteNumber', handler_input=handler_input)

        route = validate_route(bus_number)
        if route:
            handler_input.attributes_manager.session_attributes['default_route'] = obj_serializer.serialize(
                {'route_title': route.route_title, 'route_tag': route.route_tag})
        else:
            current_intent.slots['RouteNumber'].value = None
            wrong_route_speech = "The bus number is incorrect. Please provide me with a valid bus number. What is the " \
                                 "bus number?"
            wrong_route_reprompt = "What is the bus number?"
            return handler_input.response_builder.add_directive(
                ElicitSlotDirective(current_intent, 'RouteNumber')).speak(
                wrong_route_speech).ask(wrong_route_reprompt).response
        return handler_input.response_builder.add_directive(ElicitSlotDirective(current_intent, 'StopName')).speak(
            speech).ask(reprompt).response


class SetDefaultsHandlerInProgressStopName(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("SetDefaultIntent")(handler_input) and \
               get_dialog_state(handler_input) == dialog_state.DialogState.IN_PROGRESS \
               and get_slot_value(slot_name='RouteNumber', handler_input=handler_input) and \
               get_slot_value(slot_name='StopName', handler_input=handler_input) \
               and get_slot(handler_input, 'StopName').confirmation_status == SlotConfirmationStatus.NONE

    def handle(self, handler_input):
        current_intent = handler_input.request_envelope.request.intent
        reprompt = "what is the stop name you looking for?"
        speech = "Can you provide me the stop name you are looking for?"
        obj_serializer = DefaultSerializer()
        stop_val = get_slot(slot_name='StopName', handler_input=handler_input)
        default_route = handler_input.attributes_manager.session_attributes.get('default_route')
        if stop_val:
            if stop_val.resolutions:
                matches = stop_val.resolutions.resolutions_per_authority
                if matches[0].status.code == StatusCode.ER_SUCCESS_MATCH:
                    matched_stop = matches[0].values[0]
                    route = RouteConfig.get_data_route_and_agency_tag(agency_tag="umd",
                                                                      route_tag=default_route['route_tag'])
                    stop_id = matched_stop.value.id
                    if route.has_stop(stop_id):
                        stop = route.get_stop_by_id(stop_id)
                    else:
                        current_intent.slots['StopName'].value = None
                        return handler_input.response_builder.add_directive(
                            ElicitSlotDirective(current_intent, 'StopName')).speak(
                            "The stop is not a stop for this route. Please try again with a stop name or stop number "
                            "that is in this route").ask("Provide a stop name or number").response
        return handler_input.response_builder.add_directive(ConfirmSlotDirective(current_intent, 'StopName')).speak(
            "The stop you have chosen is %s. Is that okay?" % stop.stop_title).ask(
            "Please confirm the stop %s" % stop.stop_title).response


class SetDefaultsHandlerInProgressStopNameDenied(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("SetDefaultIntent")(handler_input) and \
               get_dialog_state(handler_input) == dialog_state.DialogState.IN_PROGRESS \
               and get_slot_value(slot_name='RouteNumber', handler_input=handler_input) and \
               get_slot_value(slot_name='StopName', handler_input=handler_input) \
               and get_slot(handler_input, 'StopName').confirmation_status == SlotConfirmationStatus.DENIED

    def handle(self, handler_input):
        current_intent = handler_input.request_envelope.request.intent
        current_intent.slots['StopName'].value = None
        current_intent.slots['StopName'].confirmation_status = SlotConfirmationStatus.NONE

        return handler_input.response_builder.add_directive(
            ElicitSlotDirective(current_intent, 'StopName')).speak(
            "Ok then. What is the name of the stop or stop number that you want to set default to?").ask(
            "Provide a stop name or number").response


class SetDefaultsHandlerInProgressStopNameConfirmed(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("SetDefaultIntent")(handler_input) and \
               get_dialog_state(handler_input) == dialog_state.DialogState.IN_PROGRESS \
               and get_slot_value(slot_name='RouteNumber', handler_input=handler_input) and \
               get_slot_value(slot_name='StopName', handler_input=handler_input) \
               and get_slot(handler_input, 'StopName').confirmation_status == SlotConfirmationStatus.CONFIRMED

    def handle(self, handler_input):
        current_intent = handler_input.request_envelope.request.intent
        reprompt = "what is the stop name you looking for?"
        speech = "Can you provide me the stop name you are looking for?"
        obj_serializer = DefaultSerializer()
        stop_val = get_slot(slot_name='StopName', handler_input=handler_input)
        default_route = handler_input.attributes_manager.session_attributes.get('default_route')

        matches = stop_val.resolutions.resolutions_per_authority
        if matches[0].status.code == StatusCode.ER_SUCCESS_MATCH:
            matched_stop = matches[0].values[0]
            route = RouteConfig.get_data_route_and_agency_tag(agency_tag="umd",
                                                              route_tag=default_route['route_tag'])
            stop_id = matched_stop.value.id
            if route.has_stop(stop_id):
                stop = route.get_stop_by_id(stop_id)
                handler_input.attributes_manager.session_attributes['default_stop'] = obj_serializer.serialize(
                    {'stop_id': stop.stop_id, 'direction': stop.direction, 'stop_title': stop.stop_title})
            else:
                current_intent.slots['StopName'].value = None
                return handler_input.response_builder.add_directive(
                    ElicitSlotDirective(current_intent, 'StopName')).speak(
                    "The stop is not a stop for this route. Please try again with a stop name or stop number "
                    "that is in this route").ask("Provide a stop name or number").response
        return handler_input.response_builder.add_directive(DelegateDirective(current_intent)).response


class SetDefaultsHandlerCompleted(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("SetDefaultIntent")(
            handler_input) and get_dialog_state(handler_input) == dialog_state.DialogState.COMPLETED

    def handle(self, handler_input):
        default_route = handler_input.attributes_manager.session_attributes.get('default_route')
        default_stop = handler_input.attributes_manager.session_attributes.get('default_stop')
        handler_input.attributes_manager.persistent_attributes = handler_input.attributes_manager.session_attributes
        handler_input.attributes_manager.save_persistent_attributes()
        return handler_input.response_builder.speak(
            "Thank you your defaults have been set to {}, {}".format(default_route['route_title'],
                                                                     default_stop)).response


def validate_route(route_input):
    try:
        route = RouteConfig.get_data_route_and_agency_tag(agency_tag="umd", route_tag=route_input)
        return route
    except RouteDoesNotExistException:
        return None
    except Exception as a:
        raise a