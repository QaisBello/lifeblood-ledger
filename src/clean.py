"""
Clean, anonymise and model the One Health Lifesavers blood-drive survey exports.

Input : three Google Form exports (.xlsx) in data/raw/  (NOT in this repo: they contain names,
        emails and phone numbers)
Output: data/cleaned/fact_responses.csv, dim_drive.csv, dim_donor.csv, data_quality_log.csv

Run   : python src/clean.py
"""
import pandas as pd, re, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'raw')
OUT = os.path.join(ROOT, 'data', 'cleaned'); os.makedirs(OUT, exist_ok=True)
FILES = {
 'VAL25': ("OHLS Valentine’s Day post donation evaluation (Responses).xlsx", "Valentine's Day Drive 2025", '2025-02-14'),
 'WBDD25': ("OHLS World blood donor day drive (Responses).xlsx", "World Blood Donor Day Drive 2025", '2025-06-27'),
 'VAL26': ("Val's day blood drive '26 (Responses).xlsx", "Valentine's Day Drive 2026", '2026-02-13'),
}
log = []
def L(drive, rule, n, action):
    if n: log.append(dict(drive=drive, issue=rule, rows_affected=int(n), action=action))

def col(df, *keys):
    for c in df.columns:
        if all(k.lower() in c.lower() for k in keys): return c
    return None

frames = []
for did, (fn, name, date) in FILES.items():
    df = pd.read_excel(os.path.join(SRC, fn))
    s = lambda c: df[c].astype(str).str.strip().replace({'nan': None}) if c else pd.Series([None]*len(df))
    o = pd.DataFrame({
        'source_drive': did,
        'submitted_at': pd.to_datetime(df['Timestamp']),
        'email': s(col(df,'email')).str.lower(),
        'phone': s(col(df,'phone')),
        'age_raw': s(col(df,'age')),
        'gender': s(col(df,'gender')),
        'occupation': s(col(df,'occupation')),
        'institution_raw': s(col(df,'institution')),
        'blood_group_raw': s(col(df,'blood group')),
        'genotype_raw': s(col(df,'genotype')),
        'first_time_raw': s(col(df,'first time donor')),
        'times_raw': s(col(df,'how many times')),
        'donated_raw': s(col(df,'able to donate')),
        'reason_raw': s(col(df,'why')),
        'experience_text': s(col(df,'experience')),
        'will_return_raw': s(col(df,'donate at our next')),
        'reminder_raw': s(col(df,'reminded')),
    })
    frames.append(o)
d = pd.concat(frames, ignore_index=True)
L('ALL','Raw rows loaded', len(d), '281 responses across 3 Google Form exports with different column names/orders; harmonized into one schema')

# --- drive assignment: responses submitted to the wrong form
d['drive_id'] = d['source_drive']
wrong = (d.source_drive=='VAL25') & (d.submitted_at.dt.date==pd.Timestamp('2025-06-27').date())
d.loc[wrong,'drive_id'] = 'WBDD25'
L('VAL25','Responses submitted to the Valentine 2025 form on 27 Jun 2025 (World Blood Donor Day)', wrong.sum(), 'Re-assigned to WBDD25')
late = (d.source_drive=='VAL25') & (d.submitted_at.dt.date==pd.Timestamp('2025-02-16').date())
L('VAL25','Late submission (2 days after drive)', late.sum(), 'Kept in VAL25')

# --- donor identity (anonymized)
d['phone_n'] = d.phone.fillna('').str.replace(r'\D','',regex=True).str[-10:]
d['email_n'] = d.email.fillna('').str.strip()
parent = {}
def find(x):
    while parent.setdefault(x,x)!=x: x=parent[x]
    return x
def union(a,b): parent[find(a)] = find(b)
for _,r in d.iterrows():
    keys = [k for k in ['p:'+r.phone_n if len(r.phone_n)==10 else None, 'e:'+r.email_n if '@' in r.email_n else None] if k]
    for k in keys[1:]: union(keys[0], k)
d['root'] = [find('p:'+p) if len(p)==10 else find('e:'+e) for p,e in zip(d.phone_n,d.email_n)]
# Public-safe IDs: sequential by first appearance. No hash of phone/email is kept, so IDs cannot be reversed.
_first = d.sort_values('submitted_at').root.drop_duplicates().tolist()
_seq = {r: 'D-%04d' % (i+1) for i, r in enumerate(_first)}
d['donor_id'] = d.root.map(_seq)

# within-drive duplicates
d = d.sort_values('submitted_at')
dup = d.duplicated(['donor_id','drive_id'], keep='last')
L('ALL','Same person submitted twice in the same drive', dup.sum(), 'Kept latest submission, dropped earlier one')
d = d[~dup].copy()

# --- age
a = d.age_raw.str.extract(r'(\d+)')[0].astype(float)
bad = a>=60
L('ALL','Implausible age (99, 100)', bad.sum(), 'Set to blank')
L('ALL','Age typed with text ("19 years", "19yrs", "20yrs")', d.age_raw.str.contains(r'[a-zA-Z]',na=False).sum(), 'Extracted number')
d['age'] = a.mask(bad)
d['age_band'] = pd.cut(d.age, [0,17,19,21,24,200], labels=['Under 18','18-19','20-21','22-24','25+']).astype(str).replace('nan','Unknown')
d['underage'] = d.age<18

# --- gender
g0 = d.gender.isna().sum()
d['gender'] = d.gender.fillna('Not captured')
L('VAL25','Gender blank (question added to form mid-drive)', g0, 'Labelled "Not captured"')

# --- occupation / institution
n_rare = (d.occupation.str.strip().str.title()!='Student').sum()
d['occupation'] = d.occupation.str.strip().str.title().where(lambda s: s=='Student', 'Non-student')
L('ALL','Rare occupations (e.g. one photographer) could identify a person', n_rare, 'Generalised to "Non-student"')
def inst(x):
    t = (x or '').lower()
    if t in ('','institution'): return 'Unknown'
    if 'civil servant' in t: return 'Workplace / Other'
    if any(k in t for k in ['com','medicine','lasuth','lasucon','one health','one halth']): return 'LASUCOM'
    if any(k in t for k in ['lasu','lagos state university','lagos dtat','sdg','naslasu','amsa','ahmadi']): return 'LASU (Main)'
    if any(k in t for k in ['unilag','unilorin','laau','maritime']): return 'Other University'
    return 'Workplace / Other'
d['institution_group'] = d.institution_raw.map(inst)
L('ALL','Institution typed 42 different ways (e.g. "Lasucom", "LASUCOM ", "Lagos state univ. college of medicine")', d.institution_raw.nunique(), 'Mapped to 5 groups: LASUCOM, LASU (Main), Other University, Workplace / Other, Unknown')

# --- blood group / genotype
bg = d.blood_group_raw.str.replace(' ','').str.upper()
d['blood_group'] = bg.where(bg.isin(['O+','O-','A+','A-','B+','B-','AB+','AB-']), 'Unknown')
d['abo'] = d.blood_group.str.replace(r'[+-]','',regex=True)
d['rh'] = d.blood_group.map(lambda x: 'Unknown' if x=='Unknown' else ('Rh+' if x.endswith('+') else 'Rh-'))
d['genotype'] = d.genotype_raw.where(d.genotype_raw.isin(['AA','AS','AC','SS','SC']), None)
d.loc[d.genotype_raw.notna() & d.genotype.isna(),'genotype'] = 'Unknown'
d['genotype'] = d.genotype.fillna('Not asked')

# --- donation history
def prior(r):
    t = (r.times_raw or '').lower()
    if 'first' in t or 'never' in t or 'did not' in t: return 0
    if '>' in t and '10' in t: return 11
    if '5-10' in t or '>5' in t: return 6
    m = re.search(r'\d+', t); return int(m.group()) if m else None
d['prior_donations'] = d.apply(prior, axis=1)
c1 = ((d.first_time_raw=='Yes') & (d.prior_donations>0)).sum()
L('WBDD25','Said "first-time donor = Yes" but also "donated 1 time before"', c1, 'Treated as first-time (prior = 0); the "1" most likely counts today')
d.loc[(d.first_time_raw=='Yes') & (d.prior_donations>0),'prior_donations'] = 0
c2 = ((d.first_time_raw=='No') & (d.prior_donations==0)).sum()
L('VAL25','Said "first-time donor = No" but history = "First time"', c2, 'Kept as first-time (history answer is more specific)')
L('WBDD25','History answer "Did not donate" (not a valid history option)', (d.times_raw=='Did not donate').sum(), 'Treated as no prior donations')
d['prior_bucket'] = pd.cut(d.prior_donations, [-1,0,1,2,4,100], labels=['First-timer','1 prior','2 prior','3-4 prior','5+ prior']).astype(str)
d['first_time'] = d.prior_donations==0

# --- donation outcome + deferral reason
d['donated'] = d.donated_raw=='Yes'
def reason(r):
    if r.donated: return 'Donated'
    t = (r.reason_raw or '').lower()
    if re.search(r'pcv|pvc|hb|haemo|hemo|blood count|blood level|enough|low blood|g/dl|it\'s low', t) and 'weight' not in t: return 'Low PCV / Haemoglobin'
    if re.search(r'weight|48kg|less than 50', t): return 'Low body weight'
    if re.search(r'underage|18|age', t): return 'Underage'
    if 'menstru' in t: return 'Menstruation'
    if 'fast' in t: return 'Fasting'
    if 'malaria' in t or 'drug' in t: return 'Medication'
    if r.underage: return 'Underage'
    return 'Not specified'
d['deferral_reason'] = d.apply(reason, axis=1)
inf = (~d.donated & d.underage & ~d.reason_raw.fillna('').str.lower().str.contains('age|18')).sum()
L('ALL','Deferral reason blank/vague but donor is under 18', inf, 'Reason inferred as "Underage"')
conf = (~d.donated & d.reason_raw.fillna('').str.lower().str.contains(r'i donated|^donated')).sum()
L('ALL','Answered "No, could not donate" but wrote "I donated"', conf, 'Kept the Yes/No answer; reason = "Not specified"')
L('ALL','Deferral reason written 73 free-text ways', d.reason_raw.nunique(), 'Classified into 7 reasons')

# --- intent
d['will_return'] = d.will_return_raw=='Yes'
d['wants_reminder'] = d.reminder_raw=='Yes'

# --- experience sentiment (VAL26 only)
def senti(x):
    if not x: return 'Not asked'
    t = x.lower()
    if re.search(r"didn'?t donate|did not donate|didnt get|underage|wasn't happy", t): return 'Did not donate'
    if re.search(r'stress|weird|pain(?!less)|dizzy|scary', t): return 'Mixed / Negative'
    if re.search(r'nothing special|^ok|okay|alright|fair|not bad|fine|^new$|calm', t) and not re.search(r'good|great|nice|love|chill', t): return 'Neutral'
    return 'Positive'
d['experience_sentiment'] = d.experience_text.map(senti)
L('VAL26','Respondent admits picking blood group "O" only because the field was required', 1, 'Left as reported; flag for form redesign ("I don\'t know" option exists but was missed)')

# --- donor dimension
d['drive_date'] = d.drive_id.map({k:v[2] for k,v in FILES.items()})
d['drive_name'] = d.drive_id.map({k:v[1] for k,v in FILES.items()})
d['submit_hour'] = d.submitted_at.dt.hour
order = {'VAL25':1,'WBDD25':2,'VAL26':3}
d['drive_seq'] = d.drive_id.map(order)
g = d.groupby('donor_id')
dim_donor = pd.DataFrame({
  'drives_attended': g.drive_id.nunique(),
  'first_drive': g.drive_seq.min().map({v:k for k,v in order.items()}),
  'last_drive': g.drive_seq.max().map({v:k for k,v in order.items()}),
  'times_donated_with_ohls': g.donated.sum(),
}).reset_index()
d['is_returning_to_ohls'] = d.drive_seq > d.donor_id.map(g.drive_seq.min())
d['came_back_later'] = d.drive_seq < d.donor_id.map(g.drive_seq.max())
d['has_later_drive'] = d.drive_seq < 3

d = d.sort_values('submitted_at').reset_index(drop=True)
d['submitted_at'] = d.submitted_at.dt.floor('min')  # coarsened for privacy
d['response_id'] = ['R-%04d'%(i+1) for i in range(len(d))]
fact = d[['response_id','donor_id','drive_id','drive_name','drive_date','submitted_at','submit_hour','age','age_band','underage','gender','occupation','institution_group',
          'blood_group','abo','rh','genotype','prior_donations','prior_bucket','first_time','is_returning_to_ohls','has_later_drive','came_back_later','donated','deferral_reason','reason_raw',
          'will_return','wants_reminder','experience_text','experience_sentiment']].rename(columns={'reason_raw':'deferral_reason_text'})
fact.to_csv(os.path.join(OUT,'fact_responses.csv'), index=False)
dim_donor.to_csv(os.path.join(OUT,'dim_donor.csv'), index=False)
pd.DataFrame([dict(drive_id=k, drive_name=v[1], drive_date=v[2], drive_seq=order[k], campaign='Valentine' if 'VAL' in k else 'World Blood Donor Day') for k,v in FILES.items()]).to_csv(os.path.join(OUT,'dim_drive.csv'), index=False)
pd.DataFrame(log).to_csv(os.path.join(OUT,'data_quality_log.csv'), index=False)
print(pd.DataFrame(log).to_string())
print(fact.shape, fact.donor_id.nunique(), dim_donor.drives_attended.value_counts().to_dict())
print(fact.groupby('drive_id').agg(n=('donated','size'), donated=('donated','sum')))
print(fact.deferral_reason.value_counts()); print(fact.institution_group.value_counts()); print(fact.experience_sentiment.value_counts())
