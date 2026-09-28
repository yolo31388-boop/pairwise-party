import math
import uuid

AWAY_TIMEOUT = 300
TEAM_SIZE = 5
CORE_ROLES = ("healer", "tank")


class Player:
    def __init__(self, pid, power, role):
        self.pid = pid
        self.power = power
        self.role = role
        self.away = False
        self.away_time = 0
        self.online = True


class VoiceChannel:
    def __init__(self, channel_id, members):
        self.channel_id = channel_id
        self.temporary = True
        self.members = list(members)

    def invite(self, pid):
        if pid not in self.members:
            self.members.append(pid)


class Party:
    def __init__(self):
        self.members = []
        self.leader = None
        self.vice_leader = None
        self.kick_votes = {}
        self.voice_channel = None
        self.pending_leader = None

    def add_member(self, player):
        self.members.append(player)
        if self.leader is None:
            self.leader = player.pid

    def _get(self, pid):
        for m in self.members:
            if m.pid == pid:
                return m
        return None

    def remove_member(self, pid):
        target = self._get(pid)
        if target is None:
            return False
        self.members.remove(target)
        self.kick_votes.pop(pid, None)
        if self.vice_leader == pid:
            self.vice_leader = None
        if self.leader == pid:
            self.transfer_leader()
        return True

    def vote_kick(self, initiator, target):
        if self._get(initiator) is None or self._get(target) is None:
            return False
        votes = self.kick_votes.setdefault(target, set())
        votes.add(initiator)

        others = len(self.members) - 1
        if len(self.members) <= 2:
            # 两人队伍必须双方同意（被踢者也需投赞成票）
            required = len(self.members)
        else:
            # 至少半数以上的其他队员同意
            required = max(1, math.ceil(others / 2))

        if len(votes) >= required:
            self.remove_member(target)
            return True
        return False

    def set_away(self, pid):
        member = self._get(pid)
        if member is None:
            return False
        member.away = True
        member.away_time = 0
        return True

    def set_back(self, pid):
        member = self._get(pid)
        if member is None:
            return False
        member.away = False
        member.away_time = 0
        return True

    def update_away(self, elapsed):
        """推进暂离计时，超时的队员自动踢出。"""
        timed_out = []
        for m in self.members:
            if m.away:
                m.away_time += elapsed
                if m.away_time >= AWAY_TIMEOUT:
                    timed_out.append(m.pid)
        for pid in timed_out:
            self.remove_member(pid)
        return timed_out

    def _leader_candidates(self):
        """按 副队长 > 最早加入 排序，跳过暂离/离线者。"""
        ordered = sorted(self.members, key=lambda m: self.members.index(m))
        return [
            m for m in ordered
            if m.pid != self.leader and not m.away and m.online
        ]

    def request_leader_transfer(self):
        candidates = self._leader_candidates()
        if self.vice_leader is not None:
            vice = self._get(self.vice_leader)
            if vice is not None and not vice.away and vice.online:
                candidates = [vice] + [
                    m for m in candidates if m.pid != vice.pid
                ]
        if not candidates:
            self.pending_leader = None
            return None
        self.pending_leader = candidates[0].pid
        return self.pending_leader

    def confirm_leader_transfer(self, pid):
        if pid != self.pending_leader:
            return False
        member = self._get(pid)
        if member is None or member.away or not member.online:
            # 确认时已暂离/离线，顺位跳到下一个人
            self.pending_leader = None
            self.transfer_leader()
            return False
        self.leader = pid
        self.pending_leader = None
        return True

    def transfer_leader(self):
        pid = self.request_leader_transfer()
        if pid is None:
            return None
        # 候选人均为在线且非暂离，在线即可确认
        self.confirm_leader_transfer(pid)
        return self.leader

    def on_cross_server_match(self):
        """跨服组队成功后自动创建临时语音频道并邀请全队。"""
        channel = VoiceChannel(
            "voice-" + uuid.uuid4().hex[:12],
            [m.pid for m in self.members],
        )
        self.voice_channel = channel
        return channel


class MatchMaker:
    def __init__(self):
        self.queue = []

    def find_match(self, party):
        existing_roles = {m.role for m in party.members}
        missing = [r for r in CORE_ROLES if r not in existing_roles]
        avg = self._avg_power(party)

        def sort_key(player):
            if player.role in missing:
                role_priority = missing.index(player.role)
            else:
                role_priority = len(CORE_ROLES)
            return (role_priority, abs(player.power - avg))

        candidates = sorted(self.queue, key=sort_key)
        return candidates[:TEAM_SIZE - len(party.members)]

    def search_parties(self, roles=None, mode="OR"):
        if not roles or mode == "ANY" or "any" in roles:
            # “任意”：不加职业过滤
            return list(self.queue)
        if mode == "AND":
            return [p for p in self.queue if all(r == p.role for r in roles)]
        return [p for p in self.queue if p.role in roles]

    def _avg_power(self, party):
        if not party.members:
            return 0
        return sum(m.power for m in party.members) / len(party.members)
