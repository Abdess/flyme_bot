# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
"""Handle date/time resolution for booking dialog."""

import datetime

from botbuilder.core import MessageFactory, BotTelemetryClient, NullTelemetryClient
from botbuilder.dialogs import WaterfallDialog, DialogTurnResult, WaterfallStepContext
from botbuilder.dialogs.prompts import (
    DateTimePrompt,
    PromptValidatorContext,
    PromptOptions,
    DateTimeResolution,
)
from datatypes_date_time.timex import Timex

from .cancel_and_help_dialog import CancelAndHelpDialog


class DateResolverDialog(CancelAndHelpDialog):
    """Resolve the date"""

    def __init__(
            self,
            dialog_id: str = None,
            telemetry_client: BotTelemetryClient = NullTelemetryClient(),
    ):
        super(DateResolverDialog, self).__init__(
            dialog_id or DateResolverDialog.__name__, telemetry_client
        )
        self.telemetry_client = telemetry_client
        self.dialog_id = dialog_id
        date_time_prompt = DateTimePrompt(
            DateTimePrompt.__name__, DateResolverDialog.datetime_prompt_validator
        )
        date_time_prompt.telemetry_client = telemetry_client

        waterfall_dialog = WaterfallDialog(
            WaterfallDialog.__name__ + "2", [self.initial_step, self.final_step]
        )
        waterfall_dialog.telemetry_client = telemetry_client

        self.add_dialog(date_time_prompt)
        self.add_dialog(waterfall_dialog)

        self.initial_dialog_id = WaterfallDialog.__name__ + "2"

    async def initial_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        timex = step_context.options
        prompts = {
            "str_date": "On what date would you like to travel?",
            "end_date": "On what date would you like to come back?"
        }
        prompt = prompts.get(self.dialog_id,
                             "I'm sorry, please enter a valid travel date including the month, day, and year.")
        invalid_date_msg = "Sorry, that date is invalid. Please try again."
        invalid_future_date_msg = "Sorry, time travel isn't possible yet. Please enter a valid future date."
        invalid_return_date_msg = "Returning before leaving? Please enter a valid return date."

        if timex is None:
            return await step_context.prompt(
                DateTimePrompt.__name__,
                PromptOptions(prompt=MessageFactory.text(prompt), retry_prompt=MessageFactory.text(prompt)),
            )

        try:
            date = datetime.datetime.strptime(timex.split("T")[0], '%Y-%m-%d').date()
        except ValueError:
            return await step_context.prompt(DateTimePrompt.__name__,
                                             PromptOptions(prompt=MessageFactory.text(invalid_date_msg)))

        now = datetime.datetime.now().date()

        if self.dialog_id == "str_date" and date < now:
            return await step_context.prompt(DateTimePrompt.__name__,
                                             PromptOptions(prompt=MessageFactory.text(invalid_future_date_msg)))

        if self.dialog_id == "end_date" and date < step_context.options:
            return await step_context.prompt(DateTimePrompt.__name__,
                                             PromptOptions(prompt=MessageFactory.text(invalid_return_date_msg)))

        if "definite" not in Timex(timex).types:
            return await step_context.prompt(DateTimePrompt.__name__, PromptOptions(prompt=MessageFactory.text(prompt)))

        return await step_context.next(DateTimeResolution(timex=timex))

    async def final_step(self, step_context: WaterfallStepContext):
        """Cleanup - set final return value and end dialog."""
        timex = step_context.result[0].timex
        return await step_context.end_dialog(timex)

    @staticmethod
    async def datetime_prompt_validator(prompt_context: PromptValidatorContext) -> bool:
        """ Validate the date provided is in proper form. """
        if prompt_context.recognized.succeeded:
            timex = prompt_context.recognized.value[0].timex.split("T")[0]

            # TODO: Needs TimexProperty
            return "definite" in Timex(timex).types

        return False
