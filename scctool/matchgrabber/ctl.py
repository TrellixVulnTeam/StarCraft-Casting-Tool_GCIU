"""Provide match grabber for Chobo Team League."""
import logging
from bs4 import BeautifulSoup
import requests
import re

from PyQt5.QtWidgets import QInputDialog
import scctool.settings
import scctool.settings.translation
from scctool.matchgrabber.custom import MatchGrabber as MatchGrabberParent

# create logger
module_logger = logging.getLogger(__name__)
_ = scctool.settings.translation.gettext


class MatchGrabber(MatchGrabberParent):
    """Grabs match data from Chobo Team League News."""

    _provider = "ChoboTeamLeague"

    def __init__(self, *args):
        """Init match grabber."""
        super().__init__(*args)
        self._urlprefix = "https://www.choboteamleague.com/"
        self._apiprefix = "https://alpha.tl/api?match="
        self._url = self._matchData.getURL()
        self.re_race = re.compile(
            r'^https?:\/\/i\.imgur\.com\/([^\/\.\s]+)\.png$')
        self.re_heading = re.compile(
            r'.*S(?:eason)?\s*(\d+)\s+Week\s(\d+).*$')
        self.re_teams = re.compile(r'^\s*(\S+)\s+vs\.?\s+(\S+)\s*$')
        self.team_table = {
            'QTp2T': 'Cutie Patootie',
            'JaMiT': 'JaM iT Gaming',
            'AlpX': 'Alpha X Esports',
            'TeamUR': 'Team UnRivaled',
            'BornG': 'Born Gosu',
            'GnR': 'Guns and Roaches',
            'ValidG': 'Validity Gaming',
            'FxB': 'Formless Bearsloths',
            'ScSwarm': 'SC2 Swarm',
            'dLife': 'Daily Life eSports',
            'All-In': 'All-Inspiration',
            'PiGPan': 'Taste The Bacon',
            'LiT': 'LiT eSports'
        }
        self.team_table = {k.lower(): v for k, v in self.team_table.items()}

    def grabData(self, metaChange=False, logoManager=None):
        """Grab match data."""
        self._url = self._matchData.getURL()
        matches = self.parse_article()
        if(len(matches) > 0):
            match_list = []
            for match in matches:
                if match.get('season', 0) != 0 and match.get('week', 0) != 0:
                    name = (f'S{match["season"]}W{match["week"]}: '
                            f'{match["team1"]} vs {match["team2"]}')
                else:
                    name = f'{match["team1"]} vs {match["team2"]}'
                match_list.append(name)
            match, ok = QInputDialog.getItem(
                self._controller.view, _('Select Match'),
                _('Please select a match') + ':',
                match_list, editable=False)
            if not ok:
                return
            self._rawData = matches[match_list.index(match)]
        else:
            return

        overwrite = True

        with self._matchData.emitLock(overwrite,
                                      self._matchData.metaChanged):
            self._matchData.setNoSets(7, 3, resetPlayers=overwrite)
            self._matchData.setMinSets(9)
            self._matchData.setSolo(False)
            self._matchData.setNoVetoes(0)
            self._matchData.resetLabels()
            self._matchData.setLeague(
                self._rawData.get('league', 'Chobo Team League'))
            if overwrite:
                self._matchData.resetSwap()

            for team_idx in range(2):
                name = self._rawData[f'team{team_idx + 1}']
                if not isinstance(name, str):
                    name = "TBD"
                    tag = ""
                else:
                    tag = name
                name = self.team_table.get(name.lower(), name)
                self._matchData.setTeam(
                    self._matchData.getSwappedIdx(team_idx),
                    self._aliasTeam(name), tag)
            lineups = self._rawData.get('lineups', [])
            for set_idx in range(len(lineups)):
                self._matchData.setMap(set_idx, lineups[set_idx]['map'])
                for team_idx in range(2):
                    try:
                        playername = self._aliasPlayer(
                            lineups[set_idx][f'player{team_idx+1}'])
                        if not isinstance(playername, str):
                            playername = "TBD"
                        race = str(lineups[set_idx][f'race{team_idx+1}'])
                    except Exception:
                        module_logger.exception('Error')
                        playername = 'TBD'
                        race = 'R'

                    self._matchData.setPlayer(
                        self._matchData.getSwappedIdx(team_idx),
                        set_idx,
                        playername, race)
                    if set_idx == 6:
                        self._matchData.setPlayer(
                            self._matchData.getSwappedIdx(team_idx),
                            7,
                            playername, race)
                        self._matchData.setPlayer(
                            self._matchData.getSwappedIdx(team_idx),
                            8,
                            playername, race)

            self._matchData.autoSetMyTeam(
                swap=scctool.settings.config.parser.getboolean(
                    "SCT", "swap_myteam"))

    def getURL(self, ident=False):
        """Get URL."""
        return self._url

    def convert_race(self, url):
        """Convert races from imgur image."""
        imgur = dict()
        imgur['PZaHh'] = 'T'
        imgur['lY0rg'] = 'P'
        imgur['HRNlj'] = 'Z'
        imgur['y6wDt'] = 'R'

        match = self.re_race.match(url)
        if match is None:
            return 'R'
        else:
            return imgur.get(match.group(1), 'R')

    def parse_article(self):
        r = requests.get(self._url)
        soup = BeautifulSoup(r.content, 'html.parser')
        matches = []
        for article in soup.find_all('div', class_='article'):
            heading = article.find('h2', class_='title').text.strip()
            re_match = self.re_heading.match(heading)
            if re_match is not None:
                season = int(re_match.group(1))
                week = int(re_match.group(2))
                league = f'Chobo Team League Season {season} Week {week}'
            else:
                season = 0
                week = 0
                league = 'Chobo Team League'
            content = article.find('div', class_='article-content')
            for match in content.find_all('h1'):
                match_data = {}
                re_match = self.re_teams.match(match.text.strip())
                match_data['league'] = league
                match_data['season'] = season
                match_data['week'] = week
                match_data['team1'] = re_match.group(1)
                match_data['team2'] = re_match.group(2)
                lineups = match.find_next('p')
                idx = 0
                matchups = []
                for line in lineups.find_all():
                    if line.name == 'br':
                        if len(matchups) > 0:
                            idx = idx + 1
                        continue
                    elif len(matchups) - 1 < idx:
                        matchups.append(dict())

                    if line.name == 'a':
                        if 'player1' not in matchups[idx]:
                            matchups[idx]['player1'] = line.text.strip().split(' ')[
                                0]
                        elif 'player2' not in matchups[idx]:
                            matchups[idx]['player2'] = line.text.strip().split(' ')[
                                0]
                        else:
                            module_logger.error(
                                'Number of players does not match!')
                    elif line.name == 'img':
                        if 'race1' not in matchups[idx]:
                            matchups[idx]['race1'] = self.convert_race(
                                line['src'])
                        elif 'race2' not in matchups[idx]:
                            matchups[idx]['race2'] = self.convert_race(
                                line['src'])
                        else:
                            module_logger.error(
                                'Number of races does not match!')
                    elif line.name == 'i':
                        matchups[idx]['map'] = line.text.replace(
                            '[', '').replace(']', '').replace('LE', '').strip()

                match_data['lineups'] = matchups
                matches.append(match_data)
        return matches
