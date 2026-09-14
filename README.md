# Robot Biathlon — AI Commentator

A hackathon project built at UTRA Hacks 2026 over about 26 hours: a camera rover runs an obstacle
course, and an AI watches the feed, referees the run, and **commentates it out loud** like an
Olympic broadcast.

The robot streams video from an ESP32 camera. A vision layer tracks coloured course markers to work
out where the rover is heading. A language model watches the same frames as a referee — on track,
drifting left, drifting right, off track — and writes a line of commentary, which a text-to-speech
voice reads over the live dashboard.

Behind that, a training pipeline keeps the object detector improving: run footage lands in a data
warehouse, and a nightly job pulls the new video, turns it into a labelled dataset, and retrains
the model.

> **Demo:** *(to be added)* — this drove a physical rover, so the video is the only way to show it.

## The three parts

```
vision/     OpenCV colour detection against the rover's camera stream
web/        Next.js dashboard - live feed, AI referee, spoken commentary
training/   Snowflake -> YOLO retraining pipeline, scheduled nightly
```

### vision — where is the rover pointing?

`color_detector.py` pulls the MJPEG stream from the ESP32 camera and segments it in **HSV** rather
than RGB, which is the right call for a room whose lighting nobody controls: hue stays roughly
stable as brightness changes, so a red marker is still red under a different lamp. Red needs two
ranges because it wraps around the hue circle at 0/180 — the code handles that explicitly.

Detected regions are filtered by area to drop noise, then projected into a trapezoid floor view so
a marker's position in the frame maps to a steering angle rather than just a pixel coordinate.

`vision/experiments/` keeps the eight iterations that got there, from a 60-line proof of concept to
the 180-line version before the final one. They are hackathon working files rather than polished
code, and they are kept because the progression is the honest record of how the detector was tuned
under time pressure.

### web — the referee and the voice

A Next.js dashboard with five API routes:

| Route | What it does |
|---|---|
| `/api/gemini/analyze` | sends a camera frame to Gemini 2.0 Flash under a referee system prompt; gets back structured JSON — track status, whether a target is visible, and a commentary cue |
| `/api/voice/speak` | turns that cue into speech via ElevenLabs |
| `/api/archive/upload`, `/api/archive/list` | stores and lists run footage |
| `/api/status` | system health for the dashboard |

The referee prompt is the interesting piece. It constrains the model to a fixed JSON shape and
explicitly tells it **not to stay silent** — to commit to the best-fitting status even when
uncertain. That is a deliberate choice for a live commentary application, where a referee who
abstains is worse than one who is occasionally wrong, and it is the sort of prompt decision that
only shows up once you have watched a model hedge on a blurry frame.

### training — keeping the detector current

`train_pipeline.py` runs the loop end to end:

1. connect to **Snowflake** and pull raw run videos from a stage
2. extract frames and lay them out in YOLO's expected `images/train`, `labels/train`, `images/val`,
   `labels/val` structure
3. train **YOLOv8** on the result

`setup_cron.sh` schedules it for midnight daily, `predict.py` runs inference against new footage,
and `deploy.ps1` ships the whole thing to a server. So the detector is not trained once and frozen —
every run the rover makes becomes training data for the next version.

## Running it

**The vision layer and the dashboard need the rover.** Both point at the camera's address on the
local network, hardcoded as `192.168.38.209` in `vision/color_detector.py` and
`web/components/features/TeslaVision.tsx` — change it to your own camera's address.

```bash
# vision
pip install opencv-python numpy pygame
python vision/color_detector.py

# dashboard
cd web && npm install && npm run dev

# training pipeline
cd training && pip install -r requirements.txt && python train_pipeline.py
```

Configuration is all environment variables — nothing is hardcoded:

| Variable | Used by |
|---|---|
| `GEMINI_API_KEY` | the referee |
| `ELEVENLABS_API_KEY` | the commentary voice |
| `SNOWFLAKE_ACCOUNT` / `_USER` / `_PASSWORD` / `_DATABASE` / `_SCHEMA` / `_WAREHOUSE` | the training pipeline and the archive |
| `DROPLET_IP` | the deploy and demo-fetch scripts |

YOLOv8 weights are not committed — `ultralytics` downloads `yolov8n.pt` on first use.

**Run the dashboard on your own network, not on a public host.** None of the five API routes
under `web/app/api/` check who is calling them, and each one fronts something billed or
credentialed — Gemini, ElevenLabs, and a Snowflake account with a password. Exposed to the open
internet they are an unauthenticated proxy to all three. The camera stream address is also a
hardcoded LAN IP, so the dashboard expects the rover to be on the same network as the browser.
It was built to run on a laptop next to the robot, and that is still where it belongs. Putting it
anywhere else means adding authentication in front of those routes first.

## What this is, honestly

It is a **hackathon build**: roughly a day, and a demo deadline. That shows — there are hardcoded
network addresses, eight iterations of a script kept side by side, no tests, and a dashboard that
was only ever meant to run on one laptop in one room.

What it does well is the system design. Three very different runtimes — an embedded camera, a
Python vision loop, a browser dashboard — plus three external services, wired into something that
works end to end under time pressure. And the retraining loop is a genuinely good instinct for a
weekend project: most hackathon ML stops at a model that works once, and this one is built so the
robot's own runs feed the next version.

Built at UTRA Hacks 2026. UTRA Hacks is a team robotics event and the rover itself was a
physical build, so there was a hardware side to this that lived outside this repository — but
every commit here is the software, and this repository carries no record of who else was
involved, so no attribution beyond that is claimed.
