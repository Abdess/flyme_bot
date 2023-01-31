from typing import Dict

from botbuilder.core.turn_context import TurnContext
from botbuilder.dialogs.prompts import Prompt, PromptOptions, PromptRecognizerResult
from botbuilder.schema import ActivityTypes

from config import DefaultConfig
from flight_booking_recognizer import FlightBookingRecognizer


class TextToLuisPrompt(Prompt):
    def __init__(
            self,
            dialog_id: str,
            luis_recognizer: FlightBookingRecognizer = FlightBookingRecognizer(DefaultConfig),
            validator=None,
    ):
        self.dialog_id = dialog_id
        self.luis_recognizer = luis_recognizer
        super().__init__(dialog_id, validator=validator)

    async def on_prompt(
            self,
            turn_context: TurnContext,
            state: Dict[str, object],
            options: PromptOptions,
            is_retry: bool,
    ):
        if not turn_context:
            raise TypeError("turn_context cannot be None")
        if not options:
            raise TypeError("options cannot be None")

        if is_retry and options.retry_prompt is not None:
            await turn_context.send_activity(options.retry_prompt)
        elif options.prompt is not None:
            await turn_context.send_activity(options.prompt)

    async def on_recognize(
            self,
            turn_context: TurnContext,
            state: Dict[str, object],
            options: PromptOptions,
    ) -> PromptRecognizerResult:
        if not turn_context:
            raise TypeError("turn_context cannot be None")

        if turn_context.activity.type != ActivityTypes.message:
            return PromptRecognizerResult(succeeded=False)

        user_text = turn_context.activity.text
        luis_result = await self.luis_recognizer.recognize(turn_context)
        entities = luis_result.entities.get("$instance", {})

        entity = None
        if self.dialog_id == "budget" and "money" in luis_result.entities:
            entity = f"{luis_result.entities['money'][0]['number']} {luis_result.entities['money'][0]['units']}"

        elif self.dialog_id in ["or_city", "dst_city"] and "geographyV2_city" in entities:
            entity = entities["geographyV2_city"][0]["text"].title()

        if entity:
            return PromptRecognizerResult(succeeded=True, value=entity)
        return PromptRecognizerResult(succeeded=False)
