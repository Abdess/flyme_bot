import aiounittest
from botbuilder.core import TurnContext, ConversationState, MemoryStorage
from botbuilder.core.adapters import TestAdapter
from botbuilder.dialogs import DialogSet, DialogTurnStatus

from booking_details import BookingDetails
from config import DefaultConfig
from dialogs import MainDialog, BookingDialog
from flight_booking_recognizer import FlightBookingRecognizer


class FlightBookingTest(aiounittest.AsyncTestCase):
    async def execute_booking_dialog(self, turn_context: TurnContext, dialog_id: str,
                                     booking_details: BookingDetails = None):
        dialog_context = await self.dialogs.create_context(turn_context)
        result = await dialog_context.continue_dialog()
        if result.status == DialogTurnStatus.Empty:
            if booking_details:
                await dialog_context.begin_dialog(dialog_id, booking_details)
            else:
                await dialog_context.begin_dialog(dialog_id)
        elif result.status == DialogTurnStatus.Complete:
            await turn_context.send_activity(result.result)
        await self.conversation_state.save_changes(turn_context)

    def setup_booking_dialogs(self, dialog_id, booking_details=None):
        self.conversation_state = ConversationState(MemoryStorage())
        self.dialogs_state = self.conversation_state.create_property("dialog_state")
        self.dialogs = DialogSet(self.dialogs_state)
        if dialog_id == BookingDialog.__name__:
            self.dialogs.add(BookingDialog())
            adapter = TestAdapter(lambda ctx: self.execute_booking_dialog(ctx, dialog_id, booking_details))
        else:
            config = DefaultConfig()
            luis_recognizer = FlightBookingRecognizer(config)
            booking_dialog = BookingDialog()
            self.dialogs.add(MainDialog(luis_recognizer, booking_dialog))
            adapter = TestAdapter(lambda ctx: self.execute_booking_dialog(ctx, MainDialog.__name__))
        return adapter

    async def test_flight_booking_discussion(self):
        adapter = self.setup_booking_dialogs(BookingDialog.__name__, BookingDetails())
        step1 = await adapter.test("Hi!", "To what city would you like to travel?")
        step2 = await step1.test("I want to go to Tunis!", "From what city will you be travelling?")
        step3 = await step2.test("Actually, I'm at Le Havre.", "On what date would you like to travel?")
        step4 = await step3.test("Because I'm doing an unit test, I've to tell you something futur proof... so "
                                 "let's say I want to travel during the 2nd February 2023!",
                                 "On what date would you like to come back?")
        step5 = await step4.test("I want to come back 14 days later", "What is your budget for this trip?")
        step6 = await step5.test("I've one bitcoin, some euros and 2 bananas for scale", "For how many adult(s)?")
        step7 = await step6.test("Don't know, my family say I'm still a child... so zero?", "And how many child(ren)?")
        step8 = await step7.send("Dude! I feel like I'm 1 thousand children!!")
        await step8.assert_reply("I understand that you're planning to travel to Tunis, leaving from Le Havre on "
                                 "2023-02-02 and returning on 2023-02-15. You'll be traveling with 0 adult(s) and 1000 "
                                 "child(ren), and your budget is set at 1 Bitcoin. Can you please confirm that this "
                                 "information is correct? (1) Yes or (2) No")

    async def test_flight_booking_sentence(self):
        adapter = self.setup_booking_dialogs(MainDialog.__name__)
        step1 = await adapter.test("Hey!", "Hello! What can I help you with today?")
        step2 = await step1.send("I want to go to Paris from Le Havre for the 10th February 2023 and return the "
                                 "2023-02-15. For 100€, 1 adult and 2 children.")
        await step2.assert_reply("I understand that you're planning to travel to Paris, leaving from Le Havre on "
                                 "2023-02-10 and returning on 2023-02-15. You'll be traveling with 1 adult(s) and 2 "
                                 "child(ren), and your budget is set at 100 Euro. Can you please confirm that this "
                                 "information is correct? (1) Yes or (2) No")

    async def test_flight_booking_none(self):
        adapter = self.setup_booking_dialogs(MainDialog.__name__)
        step1 = await adapter.test("Yo!", "Hello! What can I help you with today?")
        step2 = await step1.send("lmsqdkjvfl")
        await step2.assert_reply("Sorry, I only book flights. Can you please rephrase your request?")
