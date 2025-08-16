docker build -t akabot:latest .
docker tag akabot:latest codeberg.org/Akabot/Akabot:latest
docker tag akabot:latest codeberg.org/CatgirlLunya/akabot:latest
docker push codeberg.org/Akabot/Akabot:latest
docker push codeberg.org/CatgirlLunya/akabot:latest