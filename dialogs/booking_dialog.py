# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
"""Flight booking dialog."""

from datatypes_date_time.timex import Timex
import datetime

from botbuilder.dialogs import WaterfallDialog, WaterfallStepContext, DialogTurnResult
from botbuilder.dialogs.prompts import ConfirmPrompt, TextPrompt, PromptOptions
from botbuilder.core import MessageFactory, BotTelemetryClient, NullTelemetryClient
from botbuilder.schema import InputHints
from .cancel_and_help_dialog import CancelAndHelpDialog
from .date_resolver_dialog import DateResolverDialog, StrDateResolverDialog, EndDateResolverDialog

def is_ambiguous(timex: str) -> bool:
    """Ensure time is correct."""
    timex_property = Timex(timex)
    return "definite" not in timex_property.types

class BookingDialog(CancelAndHelpDialog):
    """Flight booking implementation."""

    def __init__(
        self,
        dialog_id: str = None,
        telemetry_client: BotTelemetryClient = NullTelemetryClient(),
    ):
        super(BookingDialog, self).__init__(
            dialog_id or BookingDialog.__name__, telemetry_client
        )
        self.telemetry_client = telemetry_client
        text_prompt = TextPrompt(TextPrompt.__name__)
        text_prompt.telemetry_client = telemetry_client

        text_prompt = TextPrompt(TextPrompt.__name__)
        text_prompt.telemetry_client = telemetry_client

        waterfall_dialog = WaterfallDialog(
            WaterfallDialog.__name__,
            [
                self.dst_city_step,
                self.or_city_step,
                self.str_date_step,
                self.end_date_step,
                self.budget_step,
                # self.n_adults_step,
                # self.n_children_step,
                self.confirm_step,
                self.final_step,
            ],
        )
        waterfall_dialog.telemetry_client = telemetry_client

        self.add_dialog(text_prompt)
        self.add_dialog(ConfirmPrompt(ConfirmPrompt.__name__))
        self.add_dialog(
            DateResolverDialog(DateResolverDialog.__name__, self.telemetry_client)
        )
        self.add_dialog(
            StrDateResolverDialog(StrDateResolverDialog.__name__, self.telemetry_client)
        )
        self.add_dialog(
            EndDateResolverDialog(EndDateResolverDialog.__name__, self.telemetry_client)
        )
        self.add_dialog(waterfall_dialog)

        self.initial_dialog_id = WaterfallDialog.__name__

    async def dst_city_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """Prompt for dst_city."""
        booking_details = step_context.options

        if booking_details.dst_city is None:
            return await step_context.prompt(
                TextPrompt.__name__,
                PromptOptions(
                    prompt=MessageFactory.text("To what city would you like to travel?")
                ),
            )  # pylint: disable=line-too-long,bad-continuation

        return await step_context.next(booking_details.dst_city)

    async def or_city_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Prompt for or_city city."""
        booking_details = step_context.options

        # Capture the response to the previous step's prompt
        booking_details.dst_city = step_context.result
        if booking_details.or_city is None:
            return await step_context.prompt(
                TextPrompt.__name__,
                PromptOptions(
                    prompt=MessageFactory.text("From what city will you be travelling?")
                ),
            )  # pylint: disable=line-too-long,bad-continuation

        return await step_context.next(booking_details.or_city)

    async def str_date_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """Prompt for travel date.
        This will use the DATE_RESOLVER_DIALOG."""

        booking_details = step_context.options

        # Capture the results of the previous step
        booking_details.or_city = step_context.result
        if not booking_details.str_date or self.is_ambiguous(
            booking_details.str_date
        ):
            return await step_context.begin_dialog(
                StrDateResolverDialog.__name__, booking_details.str_date
            )  # pylint: disable=line-too-long

        return await step_context.next(booking_details.str_date)

    async def end_date_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """Prompt for travel date.
        This will use the DATE_RESOLVER_DIALOG."""

        booking_details = step_context.options

        # Capture the results of the previous step
        booking_details.str_date = step_context.result
        if not booking_details.end_date or self.is_ambiguous(
            booking_details.end_date
        ):
            return await step_context.begin_dialog(
                EndDateResolverDialog.__name__, booking_details.end_date
            )  # pylint: disable=line-too-long

        return await step_context.next(booking_details.end_date)

    async def budget_step(
        self, step_context: WaterfallStepContext
        ) -> DialogTurnResult:
        booking_details = step_context.options

        # Capture the previous step's end_date
        booking_details.end_date = step_context.result
        
        #Ask for budget if it's not already set
        if booking_details.budget is None:
            message_text = "What is your budget for this trip?"
            prompt_message = MessageFactory.text(
                message_text, message_text, InputHints.expecting_input
            )
            return await step_context.prompt(
                TextPrompt.__name__, PromptOptions(prompt=prompt_message)
            )
        
        return await step_context.next(booking_details.budget)


    async def confirm_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """Confirm the information the user has provided."""
        booking_details = step_context.options

        # Capture the results of the previous step
        booking_details.budget = step_context.result
        str_date = datetime.datetime.strptime(booking_details.str_date, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(booking_details.end_date, "%Y-%m-%d").date()
        msg = (
            f"Please confirm, do you want to travel from {booking_details.or_city} to {booking_details.dst_city} on {str_date.strftime('%B %d, %Y')} "
            f"and return on {end_date.strftime('%B %d, %Y')}, with a budget of {booking_details.budget}?"
        )

        # Offer a YES/NO prompt.
        return await step_context.prompt(
            ConfirmPrompt.__name__, PromptOptions(prompt=MessageFactory.text(msg))
        )

    async def final_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Complete the interaction and end the dialog."""
        if step_context.result:
            booking_details = step_context.options

            return await step_context.end_dialog(booking_details)

        return await step_context.end_dialog()
