# Bible Reading Planner

A beginner-friendly Bible reading planner built with Python and Streamlit. It helps users create a Bible reading plan, record daily progress, adjust future assignments automatically, and share progress with groups or invited viewers.

The app uses the standard Protestant Bible chapter count: 66 books and 1,189 total chapters.

## Features

- Local sign up and login with name, username, and PIN.
- New users are sent to plan setup.
- Returning users with a plan are sent straight to progress tracking.
- Create a plan from Genesis, from a selected book/chapter, or as a mixed Old Testament/New Testament plan.
- Choose an Old Testament percentage for mixed plans.
- Select exact chapters read using chapter pickers instead of typing.
- Record progress for today or a previous date.
- Add extra progress by selecting Old Testament or New Testament, then book and chapters.
- Automatically redistribute unread chapters across future reading days.
- Track whole Bible, Old Testament, and New Testament progress.
- See projected finish timing based on current pace.
- Join groups and allow other usernames to view your progress.
- View a leaderboard ranked by Bible completion percentage.
- Add notes or reflections for each progress update.
- Export full reading history and plan to CSV.
- Export and restore user backup data as JSON.
- Includes a placeholder function for future AI reflection prompts without using an external API.

## Project Files

- `app.py` - the main Streamlit web app.
- `bible_data.py` - Bible book names, chapter counts, and Testament helpers.
- `planner.py` - plan generation, mixed-plan distribution, progress status, and recalculation logic.
- `storage.py` - SQLite saving/loading, local profiles, groups, sharing, backup, and restore.
- `utils.py` - helper functions for display and exports.
- `test_planner.py` - simple tests for planner logic.
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

When progress is saved:

1. The app records the selected progress date.
2. It marks the selected assigned chapters as completed.
3. If the user selects extra chapters, those chapters are also marked completed.
4. If the user enters only a number, the app completes the next unread chapters in order.
5. The app recalculates unread chapters.
6. Future assignments are rebuilt from the next day onward.
7. Past history is not changed.

If a reader skips a day, the app saves that nothing was read and redistributes the unread chapters into the future plan.

## Backup And Restore

Open the `Dashboard` or `Settings` page.

- Use `Export my user data` to download a JSON backup.
- Use the restore uploader to reupload that JSON after an app update.

The backup includes the current user's profile, settings, assignments, completed chapters, and reading history.

## Reset The App

Open the `Settings` page, check the reset confirmation box, and click `Reset plan`.

This resets data for the signed-in local profile.

## Run Tests

Run:

```bash
python test_planner.py
```

The tests verify:

- the Bible chapter total is 1,189;
- generated plans assign every chapter exactly once;
- mixed Old/New Testament plans cover all chapters;
- completed chapters are not reassigned;
- missed chapters are redistributed;
- future assignments update after progress.

## Deploy To Streamlit Community Cloud

1. Push this project to GitHub.
2. Go to Streamlit Community Cloud.
3. Create a new app from your GitHub repository.
4. Set the main file path to `app.py`.
5. Deploy.

The included `requirements.txt` tells Streamlit Cloud which packages to install.

## Future Ideas

- WhatsApp reminders.
- Email or push notifications.
- Proper production authentication with Supabase, Firebase, Clerk, or Auth0.
- Hosted database such as Supabase Postgres.
- AI-generated chapter reflections using OpenAI, Gemini, or a local Ollama model.
- Better mobile layouts and charts.
