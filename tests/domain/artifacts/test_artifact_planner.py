from copy import deepcopy
from projectg.domain.artifacts.models import ArtifactQualityConfig, QualityStatus
from projectg.domain.artifacts.quality import ArtifactQualityAdapter
from projectg.infrastructure.game_data.json.loader import DATASET, load_raw
from projectg.infrastructure.game_data.json.normalization import normalize_game_data
from projectg.domain.planning.config import DEFAULT_PLANNER_CONFIG
from projectg.domain.planning.dependencies import actionable_frontier
from projectg.domain.planning.gap_detector import detect_goals
from projectg.domain.planning.models import CharacterState, GoalStatus, GoalType, PlannerInput, TierValue, WeaponState
from projectg.domain.planning.scorer import score_goal
from projectg.domain.planning.today.availability import AvailabilityService
from projectg.domain.planning.today.compiler import TaskCompiler
from projectg.domain.costs.models import CostStatus, ResolvedCost
from datetime import date


def config():
    return ArtifactQualityConfig(version=2,adapter_type='rv',
        thresholds={'POOR':100,'ACCEPTABLE':200,'GOOD':300,'EXCELLENT':400})


def target(*, enabled=True, gate=None):
    return {'level':80,'ascension':5,'importance':{'level':1,'ascension':1},
        'talents':{'normal':{'enabled':False,'target':1,'importance':0},
            'skill':{'enabled':False,'target':1,'importance':0},
            'burst':{'enabled':False,'target':1,'importance':0}},
        'weapon':{'targetLevel':90,'importance':1},
        'artifact':{'enabled':enabled,'targetQuality':'GOOD','importance':1,
            'primarySets':['GoldenTroupe'],'alternativeSets':[],'gate':gate or {}}}


def planner_input(state, artifact_target, evaluation=None, domains=None):
    return PlannerInput({state.key:state},{state.key:artifact_target},{},{},{},set(),
        DEFAULT_PLANNER_CONFIG,artifact_evaluations=({state.key:evaluation} if evaluation else {}),
        artifact_quality_config=config(),artifact_domains=domains or {})


def evaluation(rv=150,fingerprint='fp'):
    return {'id':'eval-1','rawMetrics':{'rv':rv,'slots':{'flower':300,'plume':250,'sands':200,'goblet':100,'circlet':350}},
        'artifactFingerprint':fingerprint}


def test_gap_detector_missing_disabled_complete_and_below_target_semantics():
    state=CharacterState('Lauma',80,5,{'auto':1,'skill':1,'burst':1},WeaponState('w','Sword',90,6),'fp')
    missing=planner_input(state,target())
    goals,issues=detect_goals(missing)
    assert not any(goal.type==GoalType.ARTIFACT_QUALITY for goal in goals)
    assert any(issue.code=='ARTIFACT_DATA_MISSING' for issue in issues)

    disabled=planner_input(state,target(enabled=False),evaluation())
    goals,_=detect_goals(disabled)
    assert not any(goal.type==GoalType.ARTIFACT_QUALITY for goal in goals)

    complete=planner_input(state,target(),evaluation(rv=350))
    goals,_=detect_goals(complete)
    assert not any(goal.type==GoalType.ARTIFACT_QUALITY for goal in goals)

    below=planner_input(state,target(),evaluation())
    goals,_=detect_goals(below)
    goal=next(goal for goal in goals if goal.type==GoalType.ARTIFACT_QUALITY)
    assert goal.goal_key=='Lauma:ARTIFACT_QUALITY'
    assert goal.status==GoalStatus.ACTIONABLE and goal.current_value < goal.artifact_target_score
    assert goal.efficiency==0.40 and goal.artifact_weak_slots==['goblet','sands']


def test_quality_config_missing_and_gate_failure_are_structured_and_blocked():
    state=CharacterState('Lauma',80,5,{'auto':1,'skill':1,'burst':1},None,'fp')
    inp=planner_input(state,target(),evaluation())
    inp.artifact_quality_config=ArtifactQualityConfig()
    goals,issues=detect_goals(inp)
    assert not any(goal.type==GoalType.ARTIFACT_QUALITY for goal in goals)
    assert any(issue.code=='ARTIFACT_QUALITY_CONFIG_MISSING' for issue in issues)

    blocked_target=target(gate={'minLevel':90,'minAscension':6,'weaponMinLevel':90})
    goals,issues=detect_goals(planner_input(state,blocked_target,evaluation()))
    goal=next(goal for goal in goals if goal.type==GoalType.ARTIFACT_QUALITY)
    assert goal.status==GoalStatus.BLOCKED
    assert set(goal.blocked_by)=={'ARTIFACT_GATE_LEVEL','ARTIFACT_GATE_ASCENSION','ARTIFACT_GATE_WEAPON'}
    assert 'ARTIFACT_GATE_BLOCKED' in {issue.code for issue in issues}
    assert goal not in actionable_frontier(goals)


def test_artifact_required_normal_talent_gate_uses_good_auto_key():
    state=CharacterState('Lauma',80,5,{'auto':2,'skill':8,'burst':8},None,'fp')
    configured=target(gate={'requiredTalents':['normal']})
    configured['talents']['normal']={'enabled':True,'target':2,'importance':0.5}
    goals,_=detect_goals(planner_input(state,configured,evaluation()))
    goal=next(goal for goal in goals if goal.type==GoalType.ARTIFACT_QUALITY)
    assert goal.status==GoalStatus.ACTIONABLE

    state.talents['auto']=1
    goals,_=detect_goals(planner_input(state,configured,evaluation()))
    goal=next(goal for goal in goals if goal.type==GoalType.ARTIFACT_QUALITY)
    assert goal.status==GoalStatus.BLOCKED
    assert goal.blocked_by==['ARTIFACT_GATE_TALENT']


def test_artifact_scoring_uses_baseline_weights_and_artifact_efficiency_modifier():
    state=CharacterState('Lauma',80,5,{'auto':1,'skill':1,'burst':1},WeaponState('w','Sword',90,6),'fp')
    inp=planner_input(state,target(),evaluation(),{'GoldenTroupe':{'key':'DomainX','name':'Domain X'}})
    goals,_=detect_goals(inp)
    artifact=next(goal for goal in goals if goal.type==GoalType.ARTIFACT_QUALITY)
    scored=score_goal(artifact,inp)
    assert scored.score_breakdown.efficiency==0.4
    assert abs(scored.score_breakdown.efficiency_modifier-0.91)<1e-9
    assert abs(scored.score_breakdown.final_score-scored.base_score*0.91)<1e-9


def test_shared_artifact_domain_compiles_one_rng_heavy_grouped_task():
    raw=load_raw(DATASET)
    raw['domains'].append({'key':'ArtifactDomain','type':'ARTIFACT','reward_material_families':[],
        'schedule_group':'DAILY','name':'Domain X'})
    raw['artifact_sets']=[{'key':'GoldenTroupe','name':'Golden Troupe','domain_key':'ArtifactDomain'}]
    game=normalize_game_data(raw)
    assert game.artifact_sets['GoldenTroupe'].domain_key=='ArtifactDomain'
    state_a=CharacterState('Lauma',80,5,{'auto':1,'skill':1,'burst':1},None,'a')
    state_b=CharacterState('Nefer',80,5,{'auto':1,'skill':1,'burst':1},None,'b')
    goals=[]
    for state,score in ((state_a,90),(state_b,80)):
        from projectg.domain.planning.models import UpgradeGoal
        goal=UpgradeGoal(state.key+':artifact',state.key+':ARTIFACT_QUALITY',state.key,GoalType.ARTIFACT_QUALITY,
            0.2,'GOOD',1,0.7,0.7,1,0,final_score=score,title='Improve artifact',
            artifact_domain={'key':'ArtifactDomain','name':'Domain X'},efficiency=0.4,
            artifact_quality_label='POOR',artifact_target_quality='GOOD',artifact_target_score=2/3)
        goals.append(goal)
    ranked=[(goal,ResolvedCost({}, CostStatus.ESTIMATED,flags=['RNG_HEAVY'])) for goal in goals]
    sections,_=TaskCompiler(game,AvailabilityService()).compile(ranked,game_date=date(2026,9,23),
        server_region='ASIA',unresolved=[])
    tasks=sections['farming']
    assert len(tasks)==2
    assert all(task['type']=='GOAL_ACTION' for task in tasks)
    assert [task['score'] for task in tasks] == [round(goal.final_score,2) for goal in goals]
    assert all(task['farmMethods'][0]['type']=='FARM_ARTIFACT_DOMAIN' for task in tasks)


def test_quality_adapter_keeps_missing_evaluation_unknown():
    result=ArtifactQualityAdapter().evaluate(None,'GOOD',config())
    assert result.status==QualityStatus.UNKNOWN and result.normalized_score is None
