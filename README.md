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

The "content" folder holds the digital garden as markdown; the build step turns
each file into a webpage under public/.
Most pages are just text, from the "content" folder.
Some pages do not originate from the "content" folder, they are shrines or
customized pages, and have their own style.css!

## Build step

The deploy workflow (`.github/workflows/deploy.yml`) runs `python3 static_site_generator.py`
automatically on every push to `main`, then deploys `public/`. You do not need
to build before `git push`; running it locally is only for previewing:
    python3 static_site_generator.py
    python3 -m http.server 8000 --directory public

Hand-crafted pages: pages you write directly in `public/` (like
`credits.html`, or a pretty art shrine) get the sidebar and stylesheet but
are never overwritten. Add `<!-- nocontentbox -->` anywhere.

## Test step

Run the unit tests (standard library only, no dependencies):

    python3 -m unittest discover -s tests -v

Test the website in VScode terminal by running:

    python3 -m http.server 8000 --directory public

## Push step

Simply git push, and the deploy.yml mirrors the code onto the website!

## TODO

Add buttons in sidebar to link to github and linkedin.
Add a guestbook.
Include art assets from Tamagotchi Connection V3/4.5/5 and Tamagotchi corner shop 3, and concept art and promotional art.
Make the website more easily accessable from nekoweb.org AKA make a nicer banner.


## Legal    

Source code is licensed under the MIT License. Written content is licensed under CC BY-NC-SA 4.0.
Copyright © 2026 Michael Knapman. All Rights Reserved.
