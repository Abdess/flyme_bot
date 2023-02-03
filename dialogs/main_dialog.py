# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from botbuilder.core import (
    MessageFactory,
    TurnContext,
    BotTelemetryClient,
    NullTelemetryClient,
)
from botbuilder.dialogs import (
    ComponentDialog,
    WaterfallDialog,
    WaterfallStepContext,
    DialogTurnResult,
)
from botbuilder.dialogs.prompts import TextPrompt, PromptOptions
from botbuilder.schema import InputHints

from booking_details import BookingDetails
from flight_booking_recognizer import FlightBookingRecognizer
from helpers.luis_helper import LuisHelper, Intent
from .booking_dialog import BookingDialog
from .flight_itinerary_card import FlightItineraryCard


class MainDialog(ComponentDialog):
    def __init__(
            self,
            luis_recognizer: FlightBookingRecognizer,
            booking_dialog: BookingDialog,
            telemetry_client: BotTelemetryClient = NullTelemetryClient(),
    ):
        super(MainDialog, self).__init__(MainDialog.__name__)
        self.telemetry_client = telemetry_client or NullTelemetryClient()

        text_prompt = TextPrompt(TextPrompt.__name__)
        text_prompt.telemetry_client = self.telemetry_client

        booking_dialog.telemetry_client = self.telemetry_client

        wf_dialog = WaterfallDialog(
            "WFDialog", [self.intro_step, self.act_step, self.final_step]
        )
        wf_dialog.telemetry_client = self.telemetry_client

        self._luis_recognizer = luis_recognizer
        self._booking_dialog_id = booking_dialog.id

        self.add_dialog(text_prompt)
        self.add_dialog(booking_dialog)
        self.add_dialog(wf_dialog)

        self.initial_dialog_id = "WFDialog"

    async def intro_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        if not self._luis_recognizer.is_configured:
            await step_context.context.send_activity(
                MessageFactory.text(
                    "NOTE: LUIS is not configured. To enable all capabilities, add 'LuisAppId', 'LuisAPIKey' and "
                    "'LuisAPIHostName' to the appsettings.json file.",
                    input_hint=InputHints.ignoring_input,
                )
            )

            return await step_context.next(None)

        message_text = (
            str(step_context.options)
            if step_context.options
            else "Hello! What can I help you with today?"
        )
        prompt_message = MessageFactory.text(
            message_text, message_text, InputHints.expecting_input
        )

        return await step_context.prompt(
            TextPrompt.__name__, PromptOptions(prompt=prompt_message)
        )

    async def act_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        if not self._luis_recognizer.is_configured:
            # LUIS is not configured, we just run the BookingDialog path with an empty BookingDetailsInstance.
            return await step_context.begin_dialog(
                self._booking_dialog_id, BookingDetails()
            )

        # Call LUIS and gather any potential booking details. (Note the TurnContext has the response to the prompt.)
        intent, luis_result = await LuisHelper.execute_luis_query(
            self._luis_recognizer, step_context.context
        )

        bot_log = {
            "bot": "Hello! What can I help you with today?",
            "user": step_context.result,
            "step": "act_step",
            "intent": intent
        }

        if intent == Intent.BOOK_FLIGHT.value and luis_result:
            # Show a warning for or_city and dst_city if we can't resolve them.
            await MainDialog._show_warning_for_unsupported_cities(
                step_context.context, luis_result
            )
            self.telemetry_client.track_trace("Info", bot_log, "INFO")
            # Run the BookingDialog giving it whatever details we have from the LUIS call.
            return await step_context.begin_dialog(self._booking_dialog_id, luis_result)

        elif intent == Intent.CANCEL.value:
            cancel_text = "Okay, bye! Have a great day."
            cancel_message = MessageFactory.text(
                cancel_text, cancel_text, InputHints.ignoring_input
            )
            self.telemetry_client.track_trace("Cancel", bot_log, "ERROR")
            await step_context.context.send_activity(cancel_message)

        elif intent == Intent.NONE_INTENT.value:
            none_text = "Sorry, I only book flights. Can you please rephrase your request?"
            none_message = MessageFactory.text(
                none_text, none_text, InputHints.ignoring_input
            )
            self.telemetry_client.track_trace("None", bot_log, "WARNING")
            await step_context.context.send_activity(none_message)

        else:
            ambiguous_text = "I'm sorry, I didn't understand that. Can you please try asking in a different way?"
            ambiguous_message = MessageFactory.text(
                ambiguous_text, ambiguous_text, InputHints.ignoring_input
            )
            await step_context.context.send_activity(ambiguous_message)

        return await step_context.next(None)

    async def final_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        # If the child dialog ("BookingDialog") was cancelled or the user failed to confirm,
        # the Result here will be null.
        if step_context.result is not None:
            result = step_context.result

            flight_card = FlightItineraryCard(result)
            card = flight_card.create_attachment()
            response = MessageFactory.attachment(card)
            await step_context.context.send_activity(response)

            msg_txt = (
                f"Your flight is all set! It includes {result.n_adults} adult(s) and {result.n_children} child(ren)"
                f" from {result.or_city} to {result.dst_city}, departing on {result.str_date}"
                f" and returning on {result.end_date}. "
                "I've sent the booking details to your email. Have a great trip!"
            )
            message = MessageFactory.text(msg_txt, msg_txt, InputHints.ignoring_input)
            await step_context.context.send_activity(message)

        prompt_message = "Is there anything else I can help you with?"
        return await step_context.replace_dialog(self.id, prompt_message)

    @staticmethod
    async def _show_warning_for_unsupported_cities(
            context: TurnContext, luis_result: BookingDetails
    ) -> None:
        """
        Shows a warning if the requested From or To cities are recognized as entities but they are not in the Airport entity list.
        In some cases LUIS will recognize the From and To composite entities as a valid cities but the From and To Airport values
        will be empty if those entity values can't be mapped to a canonical item in the Airport.
        """
        if luis_result.unsupported_airports:
            message_text = (
                f"Sorry but the following airports are not supported:"
                f" {', '.join(luis_result.unsupported_airports)}"
            )
            message = MessageFactory.text(
                message_text, message_text, InputHints.ignoring_input
            )
            await context.send_activity(message)
