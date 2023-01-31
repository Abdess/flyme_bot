# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
from enum import Enum
from typing import Dict

from botbuilder.ai.luis import LuisRecognizer
from botbuilder.core import IntentScore, TopIntent, TurnContext

from booking_details import BookingDetails


class Intent(Enum):
    BOOK_FLIGHT = "BookFlight"
    CANCEL = "Communication_Cancel"
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
                        result.dst_city = dst_city_entities[0]["text"].title()
                    else:
                        result.unsupported_airports.append(dst_city_entities[0]["text"].title())

                or_city_entities = recognizer_result.entities.get("$instance", {}).get("or_city", [])
                if len(or_city_entities) > 0:
                    if recognizer_result.entities.get("or_city", [{"$instance": {}}]):
                        result.or_city = or_city_entities[0]["text"].title()
                    else:
                        result.unsupported_airports.append(or_city_entities[0]["text"].title())

                budget_entities = recognizer_result.entities.get("money", [])
                result.budget = None
                try:
                    if len(budget_entities) > 0:
                        result.budget = f"{budget_entities[0]['number']} {budget_entities[0]['units']}"
                except KeyError:
                    if len(budget_entities) > 1:
                        result.budget = f"{budget_entities[1]['number']} {budget_entities[1]['units']}"

                n_adults_entities = recognizer_result.entities.get("n_adults", [])
                if len(n_adults_entities) > 0:
                    result.n_adults = n_adults_entities[0]

                n_children_entities = recognizer_result.entities.get("n_children", [])
                if len(n_children_entities) > 0:
                    result.n_children = n_children_entities[0]

                date_entities = recognizer_result.entities.get("datetime", [])
                timex_range = [entity["timex"][0] for entity in date_entities if entity["type"] == "daterange"]
                timex_dates = [entity["timex"][0] for entity in date_entities if entity["type"] == "date"]

                if timex_range:
                    str_date, end_date = map(str.strip, timex_range[0].strip('()').split(','))
                elif timex_dates:
                    str_date, end_date = sorted(timex_dates)[:2]
                else:
                    raise ValueError("No valid date entities found")

                result.str_date, result.end_date = str_date, end_date

        except Exception as exception:
            print(exception)

        return intent, result
