# Bible Reading Planner

A beginner-friendly Bible reading planner built with Python and Streamlit. It helps you create a daily chapter plan, record what you actually read, and automatically adjust future assignments so you can still finish by your chosen end date.

The app uses the standard Protestant Bible chapter count: 66 books and 1,189 total chapters.

## Features

- Create a reading plan from Genesis 1 or any selected book and chapter.
- Choose a start date, end date, and reading days of the week.
- See today's assigned chapters.
- Mark today's assigned reading complete.
- Enter a different number of chapters if you read more, less, or skipped.
- Automatically redistribute unread chapters across future reading days.
- Track completed chapters, remaining chapters, percentage complete, streaks, missed days, and estimated completion date.
- Save notes or reflections for each day.
- Export reading history and the full plan to CSV.
- Reset the plan with confirmation.
- Includes a placeholder function for future AI reflection prompts without calling any external API.

## Project Files

- `app.py` - the main Streamlit web app.
- `bible_data.py` - the Bible book list and chapter counts.
- `planner.py` - plan generation, progress, and recalculation logic.
- `storage.py` - SQLite saving and loading functions.
- `utils.py` - helper functions for display and exports.
- `test_planner.py` - simple tests for the planner logic.
- `requirements.txt` - Python dependencies.
- `README.md` - setup and usage instructions.

## Install Dependencies

Make sure Python is installed. Then run:

```bash
pip install -r requirements.txt
```

## Run Locally

Start the app with:

```bash
streamlit run app.py
```

Streamlit will show a local URL in your terminal, usually:

```text
http://localhost:8501
```

Open that URL in your browser.

## How Recalculation Works

The planner keeps a canonical ordered list of Bible chapters.

When you update progress:

1. The app saves how many chapters you read today.
2. It marks completed chapters in Bible order.
3. If you read fewer than assigned, the unread chapters remain unfinished.
4. If you read more than assigned, the app marks the next unread chapters complete too.
5. Starting tomorrow, the app rebuilds the future plan using all chapters that are still unread.
6. Past history is not changed.

Example: if today's plan is Genesis 1-4 and you read 2 chapters, Genesis 1-2 are completed and Genesis 3 onward is redistributed. If you read 6 chapters, Genesis 1-6 are completed and the future daily load goes down.

## Reset the App

Open the `Settings` tab, check the reset confirmation box, and click `Reset plan`.

This deletes the local SQLite data from:

```text
bible_planner.db
```

## Run Tests

Run:

```bash
python test_planner.py
```

The tests verify:

- the Bible chapter total is 1,189;
- generated plans assign every chapter exactly once;
- duplicate chapter assignments are avoided;
- completed chapters are not reassigned;
- missed chapters are redistributed;
- extra reading moves the plan forward.

## Deploy to Streamlit Community Cloud

1. Put this project in a GitHub repository.
2. Go to Streamlit Community Cloud.
3. Create a new app from your repository.
4. Set the main file path to `app.py`.
5. Deploy.

The included `requirements.txt` tells Streamlit Cloud which packages to install.

## Future Ideas

- WhatsApp reminders.
- Email or push notifications.
- Multiple reading plans.
- Backup and restore.
- AI-generated chapter reflection prompts using OpenAI or Gemini.
- User accounts for syncing across devices.
