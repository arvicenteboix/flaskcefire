#!/bin/bash
supervisorctl reread && sudo supervisorctl update && sudo supervisorctl restart myflask
systemctl restart nginx