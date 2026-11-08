"""Sample content added the first time the app runs, so the site never looks empty."""

DEMO_BIO = "Writer, coffee lover and occasional bug whisperer. Sharing what I learn along the way."

SEED_POSTS = [
    (
        "Welcome to Inkwell: write something worth reading",
        "welcome,writing",
        """Inkwell is a small, calm place on the internet for your words. No clutter, no noise, just a clean page and an idea.

## What you can do here

- **Write in Markdown** with a live preview
- Add up to five **tags** so readers can find your posts
- Get **likes** and **comments** from other writers
- Switch between **light and dark** themes

> A blank page is not empty. It is full of everything you have not said yet.

Ready? Hit **Write** in the top bar and publish your first story. You can log in as `demo` to look around, or create your own account.
""",
    ),
    (
        "5 habits that make writing feel effortless",
        "writing,habits,productivity",
        """Good writers are not more talented than you. They just show up more often. Here are five small habits that helped me.

### 1. Write badly first
Your first draft only has to exist. Editing is where it gets good.

### 2. Keep a running ideas list
Every time something sparks your curiosity, jot it down. You will never run out of topics.

### 3. Set a tiny daily target
Even **150 words** a day adds up to a book in a year.

### 4. Read like a writer
Notice *why* a sentence works. Steal the structure, not the words.

### 5. Publish before you are ready
Perfect posts never get published. Good ones do.

Which of these will you try this week?
""",
    ),
    (
        "A beginner-friendly tour of Python dictionaries",
        "python,coding,tutorial",
        """Dictionaries are one of the most useful tools in Python. Think of them as labelled boxes: you look things up by *name* instead of by position.

```python
person = {"name": "Asha", "city": "Aligarh", "age": 21}
print(person["name"])          # Asha
person["email"] = "asha@example.com"
```

## Handy things to know

| Method | What it does |
|---|---|
| `get(key, default)` | Safe lookup without errors |
| `keys()` / `values()` | Loop over parts |
| `items()` | Loop over pairs |

```python
for key, value in person.items():
    print(key, "->", value)
```

Once dictionaries click, a huge amount of Python code suddenly makes sense.
""",
    ),
    (
        "Slow mornings: a tiny routine that changed my day",
        "life,wellbeing",
        """I used to grab my phone before I was even fully awake. Now my first ten minutes look like this:

1. A glass of water
2. Open the window and look outside
3. Three slow breaths
4. Only *then* check messages

It sounds almost too simple, but starting the day on my own terms changed how the rest of it feels. Try it for a week and see.
""",
    ),
    (
        "Why side projects teach you more than tutorials",
        "coding,career,learning",
        """Tutorials show you the path. Side projects make you **find your own**.

When you build something you actually care about, you hit real problems: confusing errors, missing features, messy data. Solving them is where the learning sticks.

Start small. A weather app, a file organizer, a personal blog. Ship it, then improve it. That loop is worth more than ten courses.
""",
    ),
    (
        "A weekend in the hills: what I packed and what I forgot",
        "travel,photography",
        """Last weekend I escaped to the hills with a small backpack and a big plan to do nothing.

**What I packed:** a warm layer, a paperback, a thermos, and my camera.

**What I forgot:** a charger. Honestly, it was the best accident of the trip. Without a screen I watched the clouds roll in and the light change on the valley, hour after hour.

Next time I will pack the same things, and forget the charger on purpose.
""",
    ),
    (
        "How to give feedback people actually enjoy receiving",
        "work,communication",
        """Feedback lands best when it is specific, kind and useful.

- Start with what worked, and be precise about it
- Describe the effect, not the person
- Offer one clear next step
- Ask a question at the end

> The goal of feedback is not to prove you noticed a problem. It is to help someone grow.
""",
    ),
]
