
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from party.match import Player, Party, MatchMaker


def test_match_considers_roles():
    mm = MatchMaker()
    party = Party()
    party.add_member(Player("p1", 100, "mage"))
    party.add_member(Player("p2", 100, "mage"))
    mm.queue = [Player("p3", 100, "healer"), Player("p4", 100, "mage")]
    result = mm.find_match(party)
    roles = [p.role for p in result]
    assert "healer" in roles


def test_away_timeout():
    party = Party()
    p = Player("p1", 100, "dps")
    party.add_member(p)
    party.set_away("p1")
    party.update_away(1000)
    assert p.away == False or "p1" not in [m.pid for m in party.members]


def test_kick_requires_majority():
    party = Party()
    party.add_member(Player("p1", 100, "dps"))
    party.add_member(Player("p2", 100, "healer"))
    assert party.vote_kick("p1", "p2") == False


def test_kick_majority_passes():
    party = Party()
    party.add_member(Player("p1", 100, "dps"))
    party.add_member(Player("p2", 100, "healer"))
    party.add_member(Player("p3", 100, "tank"))
    assert party.vote_kick("p1", "p2") == True


def test_filter_or_logic():
    mm = MatchMaker()
    mm.queue = [Player("p1", 100, "healer"), Player("p2", 100, "tank")]
    result = mm.search_parties(roles=["healer", "tank"], mode="OR")
    assert len(result) == 2


def test_auto_voice_channel():
    party = Party()
    party.add_member(Player("p1", 100, "dps"))
    party.add_member(Player("p2", 100, "healer"))
    channel = party.on_cross_server_match()
    assert channel is not None


def test_leader_transfer_order():
    party = Party()
    p1 = Player("p1", 100, "dps")
    p2 = Player("p2", 100, "healer")
    party.add_member(p1)
    party.add_member(p2)
    party.leader = "p1"
    party.transfer_leader()
    assert party.leader == "p2"


def test_away_player_skipped_as_leader():
    party = Party()
    p1 = Player("p1", 100, "dps")
    p2 = Player("p2", 100, "healer")
    party.add_member(p1)
    party.add_member(p2)
    p1.away = True
    party.leader = "p1"
    party.transfer_leader()
    assert party.leader == "p2"


def test_party_avg_power():
    mm = MatchMaker()
    party = Party()
    party.add_member(Player("p1", 100, "dps"))
    party.add_member(Player("p2", 200, "healer"))
    assert mm._avg_power(party) == 150
