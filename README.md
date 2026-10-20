# website

Michael Knapman's Website

This is my professional portfolio attached to my real name, where I publish
interesting code, cool lists, literary ideas.

I want to host the website source code on GitHub so that my content is git
tracked so you can see my projects change over time.

Every git push automatically updates https://michael.nekoweb.org/ thanks
to https://github.com/indiefellas/deploy2nekoweb
Files not able to be pushed by deploy2nekoweb such as the custom cursor
and linter are placed into the "hardcoded" folder.

There are three tracked source folders:

- `content/` - the digital garden as markdown. Each file becomes a webpage.
- `src/` - hand-written pages, images, stylesheets and other static files.
- `hardcoded/` - local-only files that are not deployed.

`public/` is generated output. It is gitignored and rebuilt from `src/` and
`content/` on every build, so never edit it by hand. Most pages are just text
from `content/`; shrines and customized pages live in `src/` and may have
their own `style.css`.

## Build step

The deploy workflow (`.github/workflows/deploy.yml`) runs `python3 static_site_generator.py`
on every push to `main`, then deploys `public/`. Locally:

    python3 static_site_generator.py
    python3 -m http.server 8000 --directory public

Hand-crafted pages: write them in `src/` (like `src/shrines.html`, or a pretty
art shrine). The build copies them into `public/` and adds the sidebar and
stylesheet, but never modifies the source. Add `<!-- nocontentbox -->`
anywhere to opt out of the central text box.

## Test step

Build first, then run the unit tests (standard library only, no dependencies):

    python3 static_site_generator.py
    python3 -m unittest discover -s tests -v

Test the website in a terminal by running:

    python3 -m http.server 8000 --directory public

## Push step

Commit your changes to `content/`, `src/`, and the build scripts, then git
push. The workflow builds the site and deploys the generated `public/` folder;
there is no generated output to commit.

## TODO

Add a guestbook.
Include art assets from Tamagotchi Connection V3/4.5/5 and Tamagotchi corner shop 3, and concept art and promotional art.
Make the website more easily accessable from nekoweb.org AKA make a nicer banner.


## Legal    

Source code is licensed under the MIT License. Written content is licensed under CC BY-NC-SA 4.0.
Copyright © 2026 Michael Knapman. All Rights Reserved.
