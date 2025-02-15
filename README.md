# Stabby Break Bot

This is a simple Twitch bot that reads a stream's thumbnail on Twitch (which updates around every 5 minutes, it seems?) and sets a timer to send a "Take a break" message to the streamer's chat whenever it detects the text `!brb`.

This is originally made for [stabbystabby's Twitch channel](https://twitch.tv/stabbystabby).

This bot uses `twitchAPI` for Twitch-specific actions, and `pytesseract` for performing OCR.
