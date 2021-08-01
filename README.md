# ft-action-zone

trading strategy for [freqtrade](https://www.freqtrade.io/) crypto bot it base on [CDC-ActionZone](https://www.tradingview.com/script/rGpAOoLi-CDC-ActionZone-V3-2020/) Indicator by [piriya33](https://www.tradingview.com/u/piriya33/)

## Clone The Repository

if you just clone this repository simple by `git clone` you need to create you self config like [this](https://www.freqtrade.io/en/latest/docker_quickstart/#docker-quick-start)

jsut type

```
# Pull the freqtrade image
docker-compose pull

# Create configuration - Requires answering interactive questions
docker-compose run --rm freqtrade new-config --config user_data/config.json
```

then

```
docker-compose up -d
```
