---
title: How to build an AI phone receptionist with Claude (Python booking agent)
description: Build the brain of an AI receptionist that answers questions, checks free times and books appointments with Claude tool use, then learn what it takes to put it on a real phone line.
kit: receptionist
date: 2026-11-25
---

Small businesses miss a lot of calls. A dental clinic is busy with a patient, a salon owner has wet hands, a repair shop is under a car. Every missed call is a booking that goes to a competitor. An AI receptionist that picks up, answers the common questions and books the appointment is one of the most useful things you can build with a large language model today.

This guide builds the part that matters most: the **conversation brain**. It answers only from the business's own information, checks real free times, books appointments without double-booking, and takes a message when it can't help. We'll build it in text first, in one Python file, with the Anthropic SDK. At the end you'll see what it takes to put a voice and a real phone number on it.

The finished code is free on GitHub: [ai-phone-receptionist-claude](https://github.com/{{owner}}/ai-phone-receptionist-claude).

## The design in one sentence

**The model decides when to use a tool. Your code decides whether it is allowed.**

Claude is good at conversation: understanding "can I come in Monday morning, but not too early?", asking one question at a time, reading back a booking. It should not be the thing that decides which times are free or whether a slot was already taken. That logic lives in plain Python, behind tools.

## Step 1: describe the business

Everything the receptionist may say comes from one file:

```json
{
  "name": "Bright Smile Dental",
  "info": "Family dental clinic at 12 Tran Phu Street. Check-up and cleaning 450,000 VND. Filling from 600,000 VND...",
  "hours": {"mon": "08:00-17:00", "sat": "08:00-12:00", "sun": ""},
  "appointment_minutes": 30,
  "booking_days_ahead": 14
}
```

For a real client this is a 15-minute conversation: services and prices, address, parking, payment, opening hours, appointment length.

## Step 2: three tools

```python
TOOLS = [
    _tool("check_availability",
          "List the free appointment start times on one day. Call it before offering times; never guess.",
          {"date": DATE}, ["date"]),
    _tool("book_appointment",
          "Book an appointment. Only after the caller agreed to a time check_availability listed, "
          "and confirmed the date, time and name you read back.",
          {"date": DATE, "time": ..., "name": ..., "phone": ..., "service": ...},
          ["date", "time", "name", "phone", "service"]),
    _tool("take_message",
          "Save a message for the owner when you cannot answer or only the owner can decide.",
          {"name": ..., "phone": ..., "reason": ...}, ["name", "phone", "reason"]),
]
```

Two details make these reliable:

- Each tool has `"strict": True` and `additionalProperties: false`, so the arguments Claude sends always match the schema. No parsing surprises.
- The **descriptions carry the rules**. "Call it before offering times; never guess" is what stops the model from inventing a 3 pm slot.

## Step 3: free times come from code

```python
def free_times(self, day):
    hours = self.biz["hours"].get(DAYS[day.weekday()], "")
    if not hours:
        return []          # closed
    ...                    # every 30-minute start between open and close
    taken = {b["time"] for b in self.bookings() if b["date"] == day.isoformat()}
    return [t for t in slots if t not in taken]
```

And when Claude calls `book_appointment`, the slot is **checked again** before saving. Two callers asking for the same time can't both get it, whatever the model believes.

## Step 4: the prompt

The system prompt is short and specific:

- Reply in the caller's language, one or two short sentences, one question at a time, no lists or markdown (it will be spoken aloud later).
- Answer only from the business info and opening hours. If you don't know, take a message.
- Discounts, refunds and complaints: don't promise anything, take a message.
- To book: ask what it is for and which day, check availability, offer two or three times, read back day, time and name, wait for a yes, then book.

The rules and business info are the same on every turn, so they're sent with `cache_control`. After the first reply, Claude reads them from the prompt cache, which is cheaper and faster.

## Step 5: the tool loop

```python
with client.beta.messages.stream(model=MODEL, system=system, tools=TOOLS,
                                 messages=messages, output_config={"effort": "low"}, ...) as stream:
    for text in stream.text_stream:
        print(text, end="")
    response = stream.get_final_message()

messages.append({"role": "assistant", "content": response.content})
for block in response.content:
    if block.type == "tool_use":
        result, is_error = run_tool(calendar, block.name, block.input)
        ...
```

Streaming matters even in text: on a phone, the voice can start speaking the first sentence while Claude writes the second. Low effort keeps replies fast, which matters more on a call than anywhere else.

A real conversation looks like this:

```
Caller: Hi, how much is a cleaning?
Receptionist: A check-up and cleaning is 450,000 dong. Would you like to book one?
Caller: Yes, Monday morning please.
Receptionist: On Monday I have 8:00, 8:30 or 9:00. Which suits you?
Caller: 8:30. I'm Lan, 0901 234 567.
Receptionist: So that's Monday the 30th at 8:30 for Lan. Shall I book it?
Caller: Yes.
Receptionist: Done, you're booked for Monday at 8:30.
```

## From text to a real phone line

The text version is the right place to get the behaviour right. Turning it into a receptionist that answers a real number adds a different set of problems:

1. **A phone line.** Twilio gives you a number and streams the call audio to your server over a WebSocket (Media Streams). You need to verify Twilio's request signature so nobody else can drive your bot.
2. **Speech to text and back.** A streaming speech recogniser (for example Deepgram Nova) turns the caller's voice into text as they speak, and a text-to-speech voice reads Claude's reply. You speak sentence by sentence, as soon as each one is ready.
3. **Interruptions.** When the caller starts talking, the receptionist must stop speaking immediately and listen. That means clearing the audio already sent to the phone.
4. **Transfers and alerts.** Urgent callers get put through to the owner's mobile, and the owner gets a Telegram or email summary after important calls.
5. **A dashboard.** Owners want to see every call, the transcript, bookings, messages and what each minute costs.
6. **Deployment.** HTTPS, a public URL for Twilio's webhook, backups, and a cost you can quote to a client (roughly 4 to 6 US cents a minute for Claude, speech and the phone line together).

## Get the full kit

If you want all of that already built and tested, the **[AI Phone Receptionist Kit]({{kit_url}})** ({{kit_price}}) is a complete FastAPI + Next.js app: Twilio and Deepgram voice with interruptions, the same booking brain, Google Calendar, SMS confirmations, owner alerts, a call dashboard with transcripts and costs, browser test calls with your microphone, and a one-command AWS deploy. You own all the code, so there is no per-minute platform fee on top.

Or start free with the [text version on GitHub](https://github.com/{{owner}}/ai-phone-receptionist-claude) and build the rest yourself.
