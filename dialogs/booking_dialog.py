# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
"""Flight booking dialog."""

from botbuilder.core import MessageFactory, BotTelemetryClient, NullTelemetryClient
from botbuilder.dialogs import WaterfallDialog, WaterfallStepContext, DialogTurnResult
from botbuilder.dialogs.prompts import ConfirmPrompt, TextPrompt, PromptOptions, NumberPrompt
from botbuilder.schema import InputHints
from datatypes_date_time.timex import Timex

from .cancel_and_help_dialog import CancelAndHelpDialog
from .date_resolver_dialog import DateResolverDialog
from .texttoluisprompt import TextToLuisPrompt


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
        number_prompt = NumberPrompt(NumberPrompt.__name__)
        number_prompt.telemetry_client = telemetry_client

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
                self.n_adults_step,
                self.n_children_step,
                self.confirm_step,
                self.final_step
            ],
        )
        waterfall_dialog.telemetry_client = telemetry_client

        self.add_dialog(number_prompt)
        self.add_dialog(text_prompt)
        self.add_dialog(TextToLuisPrompt("dst_city"))
        self.add_dialog(TextToLuisPrompt("or_city"))
        self.add_dialog(TextToLuisPrompt("budget"))
        self.add_dialog(ConfirmPrompt(ConfirmPrompt.__name__))
        self.add_dialog(
            DateResolverDialog("str_date", self.telemetry_client)
        )
        self.add_dialog(
            DateResolverDialog("end_date", self.telemetry_client)
        )
        self.add_dialog(waterfall_dialog)

        self.initial_dialog_id = WaterfallDialog.__name__

    async def dst_city_step(
            self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """Prompt for dst_city."""
        booking_details = step_context.options

        if booking_details.dst_city is None:
            retry_prompt = "Sorry, I couldn't find this place. Please enter a valid place."
            return await step_context.prompt(
                "dst_city",
                PromptOptions(
                    prompt=MessageFactory.text("To what city would you like to travel?"),
                    retry_prompt=MessageFactory.text(retry_prompt)
                ),
            )  # pylint: disable=line-too-long,bad-continuation

        return await step_context.next(booking_details.dst_city)

    async def or_city_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Prompt for or_city city."""
        booking_details = step_context.options

        # Capture the response to the previous step's prompt
        booking_details.dst_city = step_context.result

        if booking_details.or_city is None:  # origin
            retry_prompt = "Sorry, I couldn't find this place. Please enter a valid place."
            return await step_context.prompt(
                "or_city",
                PromptOptions(
                    prompt=MessageFactory.text("From what city will you be travelling?"),
                    retry_prompt=MessageFactory.text(retry_prompt)
                ),
            )  # pylint: disable=line-too-long,bad-continuation

        return await step_context.next(booking_details.or_city)  # origin

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
                "str_date", booking_details.str_date
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
                "end_date", booking_details.end_date
            )  # pylint: disable=line-too-long

        return await step_context.next(booking_details.end_date)

    async def budget_step(
            self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        booking_details = step_context.options

        # Capture the previous step's end_date
        booking_details.end_date = step_context.result

        # Ask for budget if it's not already set
        if booking_details.budget is None:
            retry_prompt = "Sorry, I couldn't process your budget input."
            "Try in a different way. Eg. 'I have a budget of 100$.'."
            return await step_context.prompt(
                "budget",
                PromptOptions(
                    prompt=MessageFactory.text("What is your budget for this trip?"),
                    retry_prompt=MessageFactory.text(retry_prompt)
                ),
            )  # pylint: disable=line-too-long,bad-continuation

        return await step_context.next(booking_details.budget)

    async def n_adults_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Prompt for the budget."""
        booking_details = step_context.options

        # Capture the response to the previous step's prompt
        booking_details.budget = step_context.result
        if booking_details.n_adults is None:
            reprompt_msg = """Please include a numerical reference in your
            sentence.
            For example: "We are 2 adults traveling." or "We are two adults.".
            """
            return await step_context.prompt(
                NumberPrompt.__name__,
                PromptOptions(
                    prompt=MessageFactory.text("For how many adult(s)?"),
                    retry_prompt=MessageFactory.text(reprompt_msg)
                ),
            )  # pylint: disable=line-too-long,bad-continuation

        return await step_context.next(booking_details.n_adults)

    async def n_children_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Prompt for the budget."""
        booking_details = step_context.options

        # Capture the response to the previous step's prompt
        booking_details.n_adults = step_context.result

        if booking_details.n_children is None:
            reprompt_msg = """Please include a numerical reference in your
            sentence.
            For example: "I have 1 children." or "I have one children.".
            """
            return await step_context.prompt(
                NumberPrompt.__name__,
                PromptOptions(
                    prompt=MessageFactory.text("And how many children(s)?"),
                    retry_prompt=MessageFactory.text(reprompt_msg)
                ),
            )  # pylint: disable=line-too-long,bad-continuation

        return await step_context.next(booking_details.n_children)

    async def confirm_step(
            self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """Confirm the information the user has provided."""
        booking_details = step_context.options

        # Capture the results of the previous step
        booking_details.n_children = step_context.result
        msg = (
            f"I understand that you're planning to travel to {booking_details.dst_city}, leaving from {booking_details.or_city} on {booking_details.str_date} and returning on {booking_details.end_date}. You'll be traveling with {booking_details.n_adults} adult(s) and {booking_details.n_children} child(ren), and your budget is set at {booking_details.budget}. Can you please confirm that this information is correct?"
        )

        # Offer a YES/NO prompt.
        return await step_context.prompt(
            ConfirmPrompt.__name__, PromptOptions(prompt=MessageFactory.text(msg))
        )

    async def final_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Complete the interaction and end the dialog."""
        if step_context.result:
            booking_details = step_context.options

        # Create data to track in App Insights
        booking_details = step_context.options

        properties = {}
        properties["or_city"] = booking_details.or_city
        properties["dst_city"] = booking_details.dst_city
        properties["str_date"] = booking_details.str_date
        properties["end_date"] = booking_details.end_date
        properties["budget"] = booking_details.budget
        properties["n_adults"] = booking_details.n_adults
        properties["n_children"] = booking_details.n_children

        # If the BOT is successful
        if step_context.result:
            # Track YES data
            self.telemetry_client.track_trace("YES answer", properties, "INFO")
            return await step_context.end_dialog(booking_details)

        # If the BOT is NOT successful
        else:
            # Send a "sorry" message to the user
            sorry_msg = "I'm sorry I couldn't help you"
            prompt_sorry_msg = MessageFactory.text(sorry_msg, sorry_msg, InputHints.ignoring_input)
            await step_context.context.send_activity(prompt_sorry_msg)

            # Track NO data
            self.telemetry_client.track_trace("NO answer", properties, "ERROR")

        return await step_context.end_dialog()

    # ==== Ambiguous date ==== #
    def is_ambiguous(self, timex: str) -> bool:
        """Ensure time is correct."""

        timex_property = Timex(timex)
        return "definite" not in timex_property.types
