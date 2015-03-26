#!/bin/sh
echo "upstream                                 fedora                                   status     repo"
for repo in $(cat golang.list); do
	python checkpackage.py $repo
done
