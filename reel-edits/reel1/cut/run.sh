PY=/home/user/new/.claude/skills/video-edit/.venv/bin/python
for n in hook plan ideas dreams; do echo "== $n"; $PY /home/user/new/.claude/skills/video-edit/scripts/cutout.py /home/user/new/reel-edits/reel1/cut/$n; done
echo ALLDONE
