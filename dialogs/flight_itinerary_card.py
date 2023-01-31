import json

from botbuilder.schema import Attachment


class FlightItineraryCard:
    def __init__(self, flight_data):
        self.flight_data = flight_data

    @staticmethod
    def _replace_placeholders(card, data):
        card_str = json.dumps(card)
        for key, value in data.items():
            pattern = "${{{}}}".format(key)
            card_str = card_str.replace(pattern, str(value))
        return json.loads(card_str)

    def create_attachment(self, path="bots/resources/FlightItineraryCard.json"):
        with open(path) as f:
            card = json.load(f)

        template_card = {
            "or_city": self.flight_data.or_city,
            "dst_city": self.flight_data.dst_city,
            "str_date": self.flight_data.str_date,
            "end_date": self.flight_data.end_date,
            "budget": self.flight_data.budget,
            "n_adults": self.flight_data.n_adults,
            "n_children": self.flight_data.n_children
        }

        flight_card = self._replace_placeholders(card, template_card)

        return Attachment(
            content_type="application/vnd.microsoft.card.adaptive", content=flight_card)
