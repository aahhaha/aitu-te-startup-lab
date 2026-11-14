import pytest
from finance import *
def test_base_scenario():
    r=calculate(Assumptions());assert r['CAC']==30;assert r['LTV_simple']==480;assert r['break_even_accounts']==25;assert r['SOM_accounts']==20
def test_ltv_sensitivity():assert calculate(Assumptions(monthly_churn=.02))['LTV_simple']>calculate(Assumptions(monthly_churn=.10))['LTV_simple']
def test_increasing_cost_increases_break_even():assert calculate(Assumptions(variable_cost=10))['break_even_accounts']>calculate(Assumptions())['break_even_accounts']
@pytest.mark.parametrize('kw',[{'price_monthly':0},{'variable_cost':31},{'monthly_churn':0},{'monthly_churn':1.1},{'new_paying_accounts':0},{'target_penetration':2},{'reachable_accounts':-1}])
def test_invalid_assumptions(kw):
    with pytest.raises(ValueError):calculate(Assumptions(**kw))
def test_zero_acquisition_spend():assert calculate(Assumptions(acquisition_spend=0))['LTV_CAC'] is None
def test_funnel_rates():assert funnel(100,20,8)=={'signup_rate':.2,'activation_rate':.4,'overall_conversion':.08}
@pytest.mark.parametrize('counts',[(0,0,0),(10,11,1),(10,5,6),(-1,0,0)])
def test_invalid_funnel(counts):
    with pytest.raises(ValueError):funnel(*counts)
