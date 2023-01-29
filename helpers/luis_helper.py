# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
from enum import Enum
from typing import Dict
from botbuilder.ai.luis import LuisRecognizer
from botbuilder.core import IntentScore, TopIntent, TurnContext

from booking_details import BookingDetails

class Intent(Enum):
    BOOK_FLIGHT = "BookFlight"
    CANCEL = "Communication.Cancel"
    CONFIRM = "Communication.Confirm"
    NONE_INTENT = "None"


def top_intent(intents: Dict[Intent, dict]) -> TopIntent:
    max_intent = Intent.NONE_INTENT
    max_value = 0.0

    for intent, value in intents:
        intent_score = IntentScore(value)
        if intent_score.score > max_value:
            max_intent, max_value = intent, intent_score.score

    return TopIntent(max_intent, max_value)


class LuisHelper:
    @staticmethod
    async def execute_luis_query(
        luis_recognizer: LuisRecognizer, turn_context: TurnContext
    ) -> (Intent, object):
        """
        Returns an object with preformatted LUIS results for the bot's dialogs to consume.
        """
        result = None
        intent = None

        try:
            recognizer_result = await luis_recognizer.recognize(turn_context)

            intent = (
                sorted(
                    recognizer_result.intents,
                    key=recognizer_result.intents.get,
                    reverse=True,
                )[:1][0]
                if recognizer_result.intents
                else None
            )

            if intent == Intent.BOOK_FLIGHT.value:
                result = BookingDetails()

                # We need to get the result from the LUIS JSON which at every level returns an array.
                dst_city_entities = recognizer_result.entities.get("$instance", {}).get("dst_city", [])
                if len(dst_city_entities) > 0:
                    if recognizer_result.entities.get("dst_city", [{"$instance": {}}]):
                        result.dst_city = dst_city_entities[0]["text"].capitalize()
                    else:
                        result.unsupported_airports.append(dst_city_entities[0]["text"].capitalize())

                or_city_entities = recognizer_result.entities.get("$instance", {}).get("or_city", [])
                if len(or_city_entities) > 0:
                    if recognizer_result.entities.get("or_city", [{"$instance": {}}]):
                        result.or_city = or_city_entities[0]["text"].capitalize()
                    else:
                        result.unsupported_airports.append(or_city_entities[0]["text"].capitalize())

                str_date, end_date = None, None

                date_entities = recognizer_result.entities.get("datetime", [])
                if date_entities:
                    timex = date_entities[0]["timex"]
                    if date_entities[0]["type"] == "daterange":
                        str_date, end_date = timex[0].replace("(", "").replace(")", "").split(",")
                    elif date_entities[0]["type"] == "date":
                        str_date = timex[0]

                result.str_date = str_date
                result.end_date = end_date


                budget_entities = recognizer_result.entities.get("$instance", {}).get(
                    "budget", []
                )
                result.budget = None
                if len(budget_entities) > 0:
                    result.budget = "$" + budget_entities[0]["text"].capitalize()

                n_adults_entities = recognizer_result.entities.get("$instance", {}).get("n_adults", [])
                if len(n_adults_entities) > 0:
                    result.n_adults = n_adults_entities[0]

                n_children_entities = recognizer_result.entities.get("$instance", {}).get("n_children", [])
                if len(n_children_entities) > 0:
                    result.n_children = n_children_entities[0]

        except Exception as exception:
            print(exception)

        return intent, result

