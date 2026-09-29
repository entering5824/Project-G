from datetime import date, datetime, timezone
from projectg.infrastructure.game_data.json.repository import get_game_data
from projectg.domain.planning.models import GoalType, UpgradeGoal
from projectg.domain.costs.models import CostStatus, ResolvedCost
from projectg.domain.costs.resolver import resolve_cost, resolve_requirements
from projectg.domain.planning.today.availability import AvailabilityService
from projectg.infrastructure.clock.game_clock import GameClock
from projectg.domain.planning.today.compiler import TaskCompiler
from projectg.domain.planning.today.models import TaskType
from projectg.bootstrap.settings import settings


def goal(key, kind=GoalType.TALENT_SKILL, score=80, current=8, target=9):
    return UpgradeGoal(id=key,goal_key=key,character_key=key.split(':')[0],type=kind,
        current_value=current,target_value=target,importance=1,deficiency=.5,tier_value=.8,
        team_value=.5,completion_value=0,final_score=score,next_milestone=target,title=key)


def resolved(required=None):
    return ResolvedCost(required or {}, CostStatus.ESTIMATED)


def test_compiler_ready_action_and_theoretical_farm_requirement():
    game = get_game_data(settings)
    compiler = TaskCompiler(game)
    g = goal("Fischl:TALENT_SKILL")

    sections, _ = compiler.compile(
        [(g, resolved({}))],
        game_date=date(2026, 9, 21),
        server_region="ASIA",
    )
    assert [x["type"] for x in sections["farming"]] == [TaskType.GOAL_ACTION]
    decision = sections["farming"][0]["goalExplanations"][0]
    assert decision["characterKey"] == "Fischl" and decision["component"] == "skill"
    assert decision["milestone"] == {"from": 8, "to": 9}

    theoretical = resolved({"Mora": 1})
    sections, _ = compiler.compile(
        [(g, theoretical)], game_date=date(2026, 9, 21), server_region="ASIA"
    )
    assert sections["quickActions"] == []
    assert sections["farming"][0]["type"] == TaskType.GOAL_ACTION
    assert sections["farming"][0]["requiredCost"] == {"Mora": 1}


def test_compiler_maps_material_sources_and_blocks_crown():
    game=get_game_data(settings); compiler=TaskCompiler(game); g=goal('Amber:CHARACTER_ASCENSION',GoalType.CHARACTER_ASCENSION)
    cases=[('PhilosophiesOfFreedom',TaskType.FARM_TALENT_DOMAIN),('BorealWolfsMilkTooth',TaskType.FARM_WEAPON_DOMAIN),
        ('CleansingHeart',TaskType.FARM_NORMAL_BOSS),('RingOfBoreas',TaskType.FARM_WEEKLY_BOSS),
        ('Mora',TaskType.FARM_MORA_LEYLINE),('CharacterEXP',TaskType.FARM_EXP_LEYLINE),
        ('WeaponEXP',TaskType.FARM_WEAPON_EXP),('PhilanemoMushroom',TaskType.COLLECT_LOCAL_SPECIALTY),
        ('DiviningScroll',TaskType.FARM_ENEMY_DROP)]
    for material,expected in cases:
        sections,issues=compiler.compile([(g,resolved({material:3}))],game_date=date(2026,9,21),server_region='ASIA')
        tasks=sections['farming']+sections['unavailable']
        assert tasks and tasks[0]['type']==TaskType.GOAL_ACTION,(material,tasks,issues)
        assert tasks[0]['farmMethods'][0]['type']==expected
    sections,_=compiler.compile([(g,resolved({'CrownOfInsight':1}))],game_date=date(2026,9,21),server_region='ASIA')
    assert not sections['blocked']
    assert sections['farming'][0]['type']==TaskType.GOAL_ACTION


def test_domains_group_and_keep_unavailable_out_of_farming_without_score_mutation():
    game=get_game_data(settings); compiler=TaskCompiler(game)
    a=goal('Amber:TALENT_SKILL',score=90); b=goal('Aloy:TALENT_BURST',score=80)
    philo='PhilosophiesOfFreedom'
    # Friday: this schedule family is closed; Sunday is globally open for domains.
    weapon=goal('YaeMiko:WEAPON_LEVEL',GoalType.WEAPON_LEVEL,score=75)
    sections,_=compiler.compile([(a,resolved({philo:2})),(b,resolved({'CleansingHeart':2})),
                                 (goal('C:TALENT',score=80),resolved({philo:1})),
                                 (weapon,resolved({'BorealWolfsMilkTooth':1}))],
                                game_date=date(2026,9,25),server_region='ASIA')
    assert len(sections['unavailable'])==2
    assert {task['primaryGoal']['goalKey'] for task in sections['unavailable']} == {a.goal_key, 'C:TALENT'}
    assert len(sections['farming'])==2
    assert [task['score'] for task in sections['unavailable']] == [90,80]
    assert a.final_score==90 and b.final_score==80
    sunday,_=compiler.compile([(a,resolved({philo:1}))],game_date=date(2026,9,27),server_region='ASIA')
    assert len(sunday['farming'])==1 and not sunday['unavailable']


def test_boss_and_mora_sources_do_not_merge_component_goals_or_add_bonus():
    game=get_game_data(settings); compiler=TaskCompiler(game)
    goals=[goal(f'C{i}:CHARACTER_LEVEL',GoalType.CHARACTER_LEVEL,score=90-i) for i in range(8)]
    for material in ('CleansingHeart', 'Mora'):
        sections,_=compiler.compile([(g,resolved({material:1})) for g in goals],
                                    game_date=date(2026,9,21),server_region='ASIA')
        tasks=sections['farming']
        assert len(tasks)==8
        assert [task['score'] for task in tasks] == [g.final_score for g in goals]
        assert all(task['type']==TaskType.GOAL_ACTION for task in tasks)


def test_cost_projection_keeps_required_family_without_inventory_simulation():
    game = get_game_data(settings)
    compiler = TaskCompiler(game)
    g = goal("Fischl:TALENT_SKILL")
    required = {"PhilosophiesOfFreedom": 3}

    cost = resolve_cost(game, required)
    assert cost.required_cost == required
    assert cost.status == CostStatus.ESTIMATED

    sections, _ = compiler.compile(
        [(g, cost)], game_date=date(2026, 9, 21), server_region="ASIA"
    )
    assert sections["farming"][0]["farmMethods"][0]["type"] == TaskType.FARM_TALENT_DOMAIN
    assert sections["farming"][0]["requiredCost"] == required


def test_game_clock_uses_region_timezone_and_reset_and_availability_is_central():
    clock=GameClock()
    # UTC Tuesday 20:30 is Wednesday 04:30 on Asia server, after server reset.
    asia=clock.now('ASIA',datetime(2026,9,22,20,30,tzinfo=timezone.utc))
    assert asia.game_date==date(2026,9,23) and asia.weekday=='WEDNESDAY'
    # 03:59 local remains the previous game day.
    before=clock.now('ASIA',datetime(2026,9,22,19,59,tzinfo=timezone.utc))
    assert before.game_date==date(2026,9,22)
    service=AvailabilityService(clock)
    assert service.is_available({'type':'TALENT_DOMAIN','schedule_group':'MON_THU'},date(2026,9,21),'ASIA')['status']=='AVAILABLE'
    assert service.is_available({'type':'TALENT_DOMAIN','schedule_group':'MON_THU'},date(2026,9,25),'ASIA')['status']=='UNAVAILABLE_TODAY'
    assert service.is_available({'type':'NORMAL_BOSS'},date(2026,9,25),'ASIA')['status']=='ALWAYS_AVAILABLE'
    assert service.is_available({'type':'TALENT_DOMAIN','schedule_group':'MON_THU'},date(2026,9,27),'ASIA')['status']=='AVAILABLE'


def test_availability_respects_resin_weekly_claims_and_temporary_source_blocks():
    no_resin = AvailabilityService(resin=0)
    result = no_resin.is_available({'type':'LEY_LINE','key':'MoraLeyline'}, date(2026,9,21), 'ASIA')
    assert result['status'] == 'UNAVAILABLE_TODAY'
    assert result['warning'] == 'INSUFFICIENT_RESIN'
    claimed = AvailabilityService(weekly_claimed={'Stormterror'})
    result = claimed.is_available({'type':'WEEKLY_BOSS','key':'Stormterror'}, date(2026,9,21), 'ASIA')
    assert result['warning'] == 'WEEKLY_REWARD_ALREADY_CLAIMED'
    blocked = AvailabilityService(unavailable_sources={'FreedomDomain'})
    result = blocked.is_available({'type':'TALENT_DOMAIN','key':'FreedomDomain',
        'schedule_group':'MON_THU'}, date(2026,9,21), 'ASIA')
    assert result['warning'] == 'SOURCE_TEMPORARILY_UNAVAILABLE'
