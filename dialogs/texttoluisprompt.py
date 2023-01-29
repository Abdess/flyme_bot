import typing

from botbuilder.dialogs.prompts import Prompt, PromptOptions, PromptRecognizerResult
from botbuilder.core.turn_context import TurnContext
from botbuilder.schema import ActivityTypes

from flight_booking_recognizer import FlightBookingRecognizer
from config import DefaultConfig
from helpers.luis_helper import LuisHelper, Intent

class TextToLuisPrompt(Prompt):
    def __init__(
        self,
        dialog_id: str,
        luis_recognizer: FlightBookingRecognizer = FlightBookingRecognizer(DefaultConfig),
        validator: typing.Callable[[str], str] = None
    ):
        self.dialog_id = dialog_id
        self.luis_recognizer = luis_recognizer
        self.detected_intent = None
        super().__init__(dialog_id, validator=validator)

    async def on_prompt(
        self,
        turn_context: TurnContext, 
        state: dict, 
        options: PromptOptions, 
        is_retry: bool,
    ):
        if not turn_context:
            raise TypeError("turn_context can't be None")
        if not options:
            raise TypeError("options can't be None")

        if is_retry and options.retry_prompt:
            await turn_context.send_activity(options.retry_prompt)
        elif options.prompt:
            await turn_context.send_activity(options.prompt)   
                
    async def on_recognize(self, turn_context: TurnContext, state: dict, options: PromptOptions) -> PromptRecognizerResult:  
        if not turn_context:
            raise TypeError("turn_context can't be None")

        if turn_context.activity.type != ActivityTypes.message:
            return PromptRecognizerResult(succeeded=False)

        usertext = turn_context.activity.text
        prompt_result = PromptRecognizerResult()
        recognizer_result = await self.luis_recognizer.recognize(turn_context)
        entities = recognizer_result.entities.get("$instance", {})
        is_valid = ["geographyV2" in key for key in entities.keys()]
        entity = entities.get(self.dialog_id, [])
        if len(entity) > 0 and True in is_valid:
            entity = entity[0]["text"].capitalize()
        elif (self.dialog_id == "or_city" or self.dialog_id == "dst_city") and "geographyV2" in recognizer_result.entities:
            entity = recognizer_result.entities["geographyV2"][0]["text"].capitalize()
        else:
            prompt_result.succeeded = False
            return prompt_result

        prompt_result.succeeded = True
        prompt_result.value = entity

        return prompt_result
