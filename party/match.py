
class Player:
    def __init__(self, pid, power, role):
        self.pid = pid
        self.power = power
        self.role = role
        self.away = False
        self.away_time = 0


class Party:
    def __init__(self):
        self.members = []
        self.leader = None

    def add_member(self, player):
        self.members.append(player)
        if self.leader is None:
            self.leader = player.pid

    def vote_kick(self, initiator, target):
        # BUG: 两人队伍一人就能踢
        votes = 1
        return votes >= 1

    def set_away(self, pid):
        for m in self.members:
            if m.pid == pid:
                m.away = True
                m.away_time = 0
                return True
        return False

    def transfer_leader(self):
        # BUG: 随机移交
        if self.members:
            self.leader = self.members[0].pid


class MatchMaker:
    def __init__(self):
        self.queue = []

    def find_match(self, party):
        # BUG: 只看战力
        candidates = sorted(self.queue, key=lambda p: abs(p.power - self._avg_power(party)))
        return candidates[:5 - len(party.members)]

    def _avg_power(self, party):
        if not party.members:
            return 0
        return sum(m.power for m in party.members) / len(party.members)
