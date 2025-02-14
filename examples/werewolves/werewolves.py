from time import sleep

from game_anywhere.core import Game, GameSummary, Agent
from game_anywhere.components import ComponentSlotProperty, Component
from game_anywhere.components.component import PerPlayer, PerPlayerComponent, Pointer
from game_anywhere.agents.chat import Chat

from enum import Enum, unique, auto
from random import shuffle
from collections import Counter
from abc import abstractmethod
from typing import TypeVar, Iterable, Literal

from game_anywhere.core.agent import AgentId

T = TypeVar('T')

def uniq_c(it: Iterable[T]) -> Iterable[tuple[T, int]]:
    """ see: `uniq -c`. Why isn't this in itertools? """
    prev_val, counter = None, 0
    for i in it:
        if i != prev_val:
            if counter != 0:
                yield prev_val, counter
            prev_val = i
            counter = 1
        else:
            counter += 1
    yield prev_val, counter


@unique
class Team(Enum):
    VILLAGE = auto()
    WEREWOLVES = auto()
    NEUTRAL = auto()


class Player(PerPlayerComponent):
    alive = ComponentSlotProperty(content=True)
    role = ComponentSlotProperty(hidden=True)


class RoleCard(Component):
    """ A very simple class representing a role card. """
    def __init__(self, role: str):
        super().__init__()
        self.role = role
    def __str__(self):
        return self.role


class Role(Component):
    """
    Represents a role, including powers as methods, current state of the role (e.g. power already used), etc.
    Role is basically a discriminated union of all possible roles,
    and they have a `card` slot that is the discriminant.
    """
    all: dict[str, type["Role"]] = {}

    card = ComponentSlotProperty()

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        Role.all[cls.__name__] = cls

    @property
    @abstractmethod
    def ALLEGIANCE(self) -> Team: ...

    def __init__(self):
        super().__init__()
        self.allegiance = self.ALLEGIANCE
        self.card = RoleCard(type(self).__name__)

    @classmethod
    @abstractmethod
    def wake_up(cls, game: 'Werewolves', players: list[Player]):
        ...

    HIDDEN_HTML = "(hidden role)"


class Werewolves(Game):
    class Win(GameSummary, Exception):
        def __init__(self, whowon: Literal[Team.VILLAGE,Team.WEREWOLVES]|str, winners: list[Player]):
            self.whowon = whowon
            self.winners = winners
        def get_winner(self) -> AgentId:
            pass

    players = PerPlayer(Player)
    mayor = ComponentSlotProperty(slotType=Pointer)

    @classmethod
    def parse_config(cls, config: list[str]) -> dict[Literal['all_roles'], list[type[Role]]]:
        return {'all_roles': [Role.all[rolename] for rolename in config]}

    def __init__(self, agent_descriptions, all_roles: list[type[Role]]):
        super().__init__(agent_descriptions, nb_agents=len(all_roles))
        self.werewolf_kill: Player|None = None
        self.other_kills: list[Player] = []
        self.lovers: set[Player]|None = None
        self.all_roles = all_roles

    def set_agents(self, agents: list[Agent]):
        super().set_agents(agents)
        # we have to reset that now that the real agents are available
        # TODO: this is very ugly
        self.players: list[Player] = PerPlayer.INIT  # type: ignore

        # and now we can also distribute the roles
        shuffle(self.all_roles)
        for player, roleType in zip(self.players, self.all_roles):
            player.role = roleType()

    def chat(self, players: Iterable[Player]):
        return Chat([player.owner for player in players])

    def kill(self, player: Player):
        # TODO check for special powers preventing their death (or e.g. Maid)
        if self.mayor == player:
            successor = player.owner.choose_one_component_slot(self.alive_players, message="Choose your successor as mayor").owner
            self.mayor = successor
        player.role.card.reveal()
        player.alive = False
        power_balance = Counter((player.role.allegiance for player in self.alive_players))
        if len(power_balance) == 1:
            raise self.Win(whowon=next(iter(power_balance.keys())), winners=self.alive_players)
        elif len(self.alive_players) == 2 and set(self.alive_players) == self.lovers:
            raise self.Win(whowon='lovers', winners=self.alive_players)

    def night(self, first=False):
        FIRST_NIGHT_ORDER = [Cupid, Seer, Werewolf, Witch]
        NIGHT_ORDER = [Seer, Werewolf, Witch]

        order = FIRST_NIGHT_ORDER if first else NIGHT_ORDER
        for role in order:
            players = [player for player in self.alive_players if type(player.role) == role]
            print('Waking up', role, 'with players', players)
            if players:
                role.wake_up(self, players)

        if self.werewolf_kill is not None:
            self.kill(self.werewolf_kill)

        for kill in self.other_kills:
            self.kill(kill)

    def day(self):
        with self.chat(self.alive_players):
            # TODO: maybe people can change their vote until the last moment
            if self.mayor is None:
                while True:
                    print('Electing mayor')
                    votes = collect_votes(self.alive_players, self, message="Choose a Mayor")
                    votes = count_votes(votes)
                    result = get_top_vote(votes)
                    if result is None:
                        self.message('No mayor chosen, new vote')
                    else:
                        self.mayor = result
                        break
            print('Killing')
            kill_votes = collect_votes(self.alive_players, self, message="Choose who should be executed")
            kill_results = count_votes(kill_votes)
            if self.mayor in kill_votes:
                kill_results[kill_votes[self.mayor]] += 1.1
                # mayor has one additional vote plus tiebreaker (modeled as 0.1)
            victim = get_top_vote(kill_results)
            self.kill(victim)

    def play_game(self) -> GameSummary:
        try:
            self.night(first=True)
            while True:
                self.day()
                self.night()
        except Werewolves.Win as summary:
            return summary

    @property
    def alive_players(self) -> list[Player]:
        return list(filter(lambda p: p.alive, self.players))

    def alive_player_slots(self) -> list['ComponentSlot']:
        return [slot for slot in self.players.slots if slot.content.alive]


ABSTENTION = 'Abstain'

def collect_votes(voters: list[Player], game: 'Werewolves', message: str) -> dict[Player, Player]:
    votes = {}
    for player in voters:
        choice = player.owner.choose_one_component_slot(
            game.alive_player_slots(), special_options=[ABSTENTION],
            message=message,
        )
        if choice != ABSTENTION:
            votes[player] = choice.content
    return votes


def count_votes(votes: dict[Player, Player]) -> dict[Player, int]:
    votes: Iterable[Player] = votes.values()
    votes = sorted(votes, key=lambda p: id(p))
    return {key: nbvotes for key, nbvotes in uniq_c(votes)}


def get_top_vote(votes: dict[Player, int]) -> Player|None:
    votes: list[tuple[Player, int]] = list(zip(votes.keys(), votes.values()))
    if len(votes) == 0:
        return None
    results = sorted(votes, key=lambda tup: tup[1], reverse=True)
    if len(results) > 1 and results[1][1] == results[0][1]:
        return None # tied vote
    return results[0][0]


class Villager(Role):
    ALLEGIANCE = Team.VILLAGE

    @classmethod
    def wake_up(cls, *args, **kwargs):
        raise AssertionError('Villagers are not woken up during the night!')


class Werewolf(Role):
    ALLEGIANCE = Team.WEREWOLVES

    @classmethod
    def wake_up(cls, game: Werewolves, players: list[Player]):
        game.werewolf_kill = None
        with game.chat(players) as chat:
            votes = collect_votes(players, game, message="Vote who your Werewolf pack should kill")
            votes = count_votes(votes)
            game.werewolf_kill = get_top_vote(votes)
            print("Chose werewolf kill as", game.werewolf_kill, ". Closing chat room...")
        print("Closed chat room, werewolves go to sleep")


class Cupid(Role):
    ALLEGIANCE = Team.VILLAGE

    @classmethod
    def wake_up(cls, game: Werewolves, players: list[Player]):
        cupid, = players
        singles = game.alive_player_slots()
        lover1 = cupid.owner.choose_one_component_slot(players, message="Choose the first lover").content
        singles.remove(lover1)
        lover2 = cupid.owner.choose_one_component_slot(players, message="Choose another lover").content
        game.lovers = {lover1, lover2}
        with game.chat(players=[lover1, lover2]):
            sleep(10)


class Seer(Role):
    ALLEGIANCE = Team.VILLAGE

    @classmethod
    def wake_up(cls, game: Werewolves, players: list[Player]):
        seer, = players
        seen = seer.owner.choose_one_component_slot(game.alive_player_slots(), message="Choose whose role you want to See").content
        seen.role.card.reveal(to=seer)


class Witch(Role):
    ALLEGIANCE = Team.VILLAGE

    @classmethod
    def wake_up(cls, game: Werewolves, players: list[Player]):
        witch, = players
        if game.werewolf_kill is not None:
            witch.owner.message('This player has been killed by the werewolves:' + game.werewolf_kill.owner.name, highlight=game.werewolf_kill)
            if witch.role.has_healing_potion:
                if witch.owner.boolean_choice("Use healing potion"):
                    witch.role.has_healing_potion = False
                    game.werewolf_kill = None
        if witch.role.has_poison:
            if witch.owner.boolean_choice("Use poison"):
                witch.role.has_poison = False
                killed = witch.owner.choose_one_component_slot(game.alive_player_slots(), message="Choose who to kill").content
                game.other_kills.append(killed)

    def __init__(self):
        super().__init__()
        self.has_healing_potion, self.has_poison = True, True


if __name__ == "__main__":
    from game_anywhere.run_game import run_game_from_cmdline
    run_game_from_cmdline(Werewolves)
