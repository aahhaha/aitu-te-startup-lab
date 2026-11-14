"""Scenario calculations for ClearQuestion; assumptions are not actual sales."""
from dataclasses import dataclass,asdict
import json,math
@dataclass(frozen=True)
class Assumptions:
    price_monthly:float=30
    variable_cost:float=6
    fixed_monthly:float=600
    acquisition_spend:float=300
    new_paying_accounts:int=10
    monthly_churn:float=.05
    reachable_accounts:int=200
    target_penetration:float=.10
    def validate(self):
        if self.price_monthly<=0 or self.variable_cost<0 or self.fixed_monthly<0 or self.acquisition_spend<0:raise ValueError('Invalid cost or price')
        if self.variable_cost>=self.price_monthly:raise ValueError('Positive contribution required')
        if self.new_paying_accounts<=0:raise ValueError('CAC requires at least one acquisition')
        if not 0<self.monthly_churn<=1 or not 0<=self.target_penetration<=1 or self.reachable_accounts<0:raise ValueError('Invalid rate or market')
def calculate(a:Assumptions):
    a.validate();margin=a.price_monthly-a.variable_cost;cac=a.acquisition_spend/a.new_paying_accounts;ltv=margin/a.monthly_churn
    return {'data_kind':'planning assumptions, not observed sales','contribution_per_account':margin,'CAC':cac,'LTV_simple':ltv,'LTV_CAC':ltv/cac if cac else None,'payback_months':cac/margin,'break_even_accounts':math.ceil(a.fixed_monthly/margin),'SOM_accounts':math.floor(a.reachable_accounts*a.target_penetration),'assumptions':asdict(a)}
def funnel(visitors,signups,activated):
    if not 0<=activated<=signups<=visitors or visitors<=0:raise ValueError('Invalid funnel counts')
    return {'signup_rate':signups/visitors,'activation_rate':activated/signups if signups else 0,'overall_conversion':activated/visitors}
if __name__=='__main__':
    print(json.dumps({'base':calculate(Assumptions()),'sensitivity':[calculate(Assumptions(monthly_churn=c)) for c in [.02,.05,.10]],'synthetic_funnel':funnel(100,20,8)},indent=2))
