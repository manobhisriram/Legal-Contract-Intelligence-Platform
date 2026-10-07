"""
Red-Teaming Suite — 50 adversarial contracts designed to test agent failure modes.
Categories:
1. Buried data rights waivers (10 contracts)
2. Disguised liability caps in complex formulas (10 contracts)
3. Auto-renewal with unusual terminology (10 contracts)
4. Cross-reference exploits (10 contracts)
5. Mixed language contracts (10 contracts)
"""
from typing import Dict, Any, List
from datetime import datetime

from backend.core.logging import get_logger
from backend.core import metrics

logger = get_logger(__name__)

# Adversarial contract templates — each designed to trick the reviewer
ADVERSARIAL_CONTRACTS = {
    "buried_data_rights": [
        {
            "id": "adv_001",
            "category": "buried_data_rights",
            "description": "Data rights waiver buried inside 'service improvement' clause",
            "hidden_risk": "data_rights_waiver",
            "expected_detection": True,
            "contract_text": """
MASTER SERVICES AGREEMENT

1. SERVICES
Provider shall deliver software services as described in Schedule A.

2. PAYMENT TERMS
Client shall pay invoices within thirty (30) days of receipt. Late payments 
shall accrue interest at 1.5% per month.

3. SERVICE IMPROVEMENT AND ANALYTICS
In order to continuously improve and enhance the quality, performance, and 
features of our platform for all customers, Provider may collect, analyze, 
process, and utilize anonymized and aggregated usage data, interaction 
patterns, user behavior analytics, and similar operational metrics. 
Notwithstanding any other provision of this Agreement, and in consideration 
for the favorable pricing provided hereunder, Client hereby grants to 
Provider a perpetual, irrevocable, worldwide, royalty-free license to use 
Client's data, including all content, inputs, outputs, and derivatives 
thereof, to train, fine-tune, validate, and improve Provider's artificial 
intelligence and machine learning models and systems. This license shall 
survive termination of this Agreement.

4. INTELLECTUAL PROPERTY
All pre-existing intellectual property of each party remains owned by that 
party. Work product created specifically for Client shall be owned by Client.

5. CONFIDENTIALITY
Each party agrees to maintain the confidentiality of the other party's 
proprietary information for a period of three (3) years.

6. TERM AND TERMINATION
This Agreement shall continue for one (1) year and automatically renew 
for successive one-year terms.
""",
        },
        {
            "id": "adv_002",
            "category": "buried_data_rights",
            "description": "Training data clause hidden in definitions section",
            "hidden_risk": "data_rights_waiver",
            "expected_detection": True,
            "contract_text": """
SOFTWARE LICENSE AGREEMENT

DEFINITIONS
"Service Data" means any data, content, or information submitted to or 
processed by the Service, including but not limited to all inputs, outputs, 
queries, responses, and metadata. "Anonymized Service Data" means Service 
Data that has been processed to remove personally identifiable information, 
which Provider may use without restriction including for model training, 
product development, benchmarking, and commercial purposes. Client 
acknowledges that Anonymized Service Data includes semantic patterns, 
query structures, and response characteristics derived from Client's usage.

1. LICENSE GRANT
Subject to the terms of this Agreement, Provider grants Client a 
non-exclusive, non-transferable license to use the Service.

2. FEES
Annual subscription fees as set forth in the Order Form are due upon 
execution and annually thereafter.

3. LIMITATION OF LIABILITY
PROVIDER'S TOTAL LIABILITY SHALL NOT EXCEED THE GREATER OF (A) THE FEES 
PAID IN THE THREE MONTHS PRECEDING THE CLAIM OR (B) ONE THOUSAND DOLLARS.

4. GOVERNING LAW
This Agreement shall be governed by the laws of the State of Delaware.
""",
        },
        {
            "id": "adv_003",
            "category": "buried_data_rights",
            "description": "Data rights buried in feedback and improvement clause",
            "hidden_risk": "data_rights_waiver",
            "expected_detection": True,
            "contract_text": """
PLATFORM SERVICES AGREEMENT

1. GRANT OF LICENSE
Provider grants Client a non-exclusive license to access the Platform.

2. FEES
Annual subscription fee of $120,000 payable quarterly.

3. FEEDBACK AND PRODUCT IMPROVEMENT
Client acknowledges that Provider values product improvement. If Client
voluntarily provides feedback, suggestions, or reports regarding the
Platform ("Feedback"), Client grants Provider an unrestricted, perpetual,
irrevocable, worldwide license to use such Feedback. Additionally, to
enable Provider to improve service quality and develop new features,
Client grants Provider the right to process, analyze, and learn from
all Client data processed through the Platform, provided that Provider
will use commercially reasonable efforts to anonymize such data prior
to use in product development activities including machine learning
model training and improvement.

4. CONFIDENTIALITY
Each party agrees to keep the other party's confidential information
confidential for five (5) years.
""",
        },
        {
            "id": "adv_004",
            "category": "buried_data_rights",
            "description": "Training rights granted via 'operational analytics' language",
            "hidden_risk": "data_rights_waiver",
            "expected_detection": True,
            "contract_text": """
ENTERPRISE SOFTWARE SUBSCRIPTION

1. THE SERVICE
Access to Provider's AI-powered platform as described in the Order Form.

2. OPERATIONAL ANALYTICS AND BENCHMARKING
To provide industry benchmarks and market intelligence as part of the
Service, Provider operates an Operational Analytics Program. Participation
is a condition of receiving the Service at the subscription rate specified
in the Order Form. Under this Program, Provider collects and processes
metadata, usage patterns, query structures, and outputs from Client's
use of the Service. This data is used to: (i) generate industry
benchmarks; (ii) improve Provider's AI models; (iii) train and validate
machine learning systems; and (iv) develop new product features.
Client may opt out by paying the non-participation rate of 2.4x the
subscription fee listed in the Order Form.

3. TERM
Initial term of 24 months. Early termination penalty equals remaining
contract value.
""",
        },
        {
            "id": "adv_005",
            "category": "buried_data_rights",
            "description": "AI training rights in technical support clause",
            "hidden_risk": "data_rights_waiver",
            "expected_detection": True,
            "contract_text": """
MANAGED SERVICES AGREEMENT

1. SERVICES
Provider will provide managed IT services as detailed in Schedule 1.

2. TECHNICAL SUPPORT
Provider provides 24/7 technical support. When Client submits support
tickets, logs, or diagnostic data to Provider, Client acknowledges
that such submissions may include system data, error messages, and
operational information. To improve support quality and enable Provider
to resolve future issues more efficiently, Client grants Provider a
perpetual license to retain, analyze, and incorporate patterns from
support submissions into Provider's knowledge base and AI-assisted
support systems, including use of such patterns for training automated
support models.

3. SLA
99.5% uptime SLA. Credits for downtime below SLA.
""",
        },
        {
            "id": "adv_006",
            "category": "buried_data_rights",
            "description": "Model training rights granted via 'service quality' consent buried in definitions",
            "hidden_risk": "data_rights_waiver",
            "expected_detection": True,
            "contract_text": """
SAAS SUBSCRIPTION AGREEMENT

DEFINITIONS
"Service Quality Data" means any data, metadata, telemetry, performance
metrics, usage logs, feature interaction data, and derived insights
generated in connection with Client's use of the Service, excluding
personally identifiable information. Provider may collect, retain, use,
and license Service Quality Data without restriction, including for
the purposes of training, validating, and improving Provider's
artificial intelligence systems, developing new products, and
commercial benchmarking. Client's access to and use of the Service
constitutes consent to this collection and use.

1. LICENSE
Subject to these terms, Provider grants Client access to the Service.

2. FEES
As set forth in the applicable Order Form.

3. LIMITATION OF LIABILITY
Provider's liability is limited to fees paid in the previous 60 days.
""",
        },
        {
            "id": "adv_007",
            "category": "buried_data_rights",
            "description": "Data export clause that grants reverse rights to Provider",
            "hidden_risk": "data_rights_waiver",
            "expected_detection": True,
            "contract_text": """
DATA PLATFORM AGREEMENT

1. DATA EXPORT
Client may export their data at any time using Provider's export tools.
All data exports are provided in Provider's standard format. Provider
retains copies of all exported data for audit and compliance purposes
for a minimum of 7 years. Provider may use retained copies for
internal analytics, service improvement, and to train automated
systems to better detect anomalies and improve data quality recommendations.

2. DATA PROCESSING
Provider processes Client data solely to provide the Service, except
as described in Section 1 and the Provider Privacy Policy (available
at provider.com/privacy, which may be updated from time to time).

3. PAYMENT
$50,000 per year. Net 30 payment terms.
""",
        },
        {
            "id": "adv_008",
            "category": "buried_data_rights",
            "description": "Benchmark rights clause enabling competitive intelligence use of Client data",
            "hidden_risk": "data_rights_waiver",
            "expected_detection": True,
            "contract_text": """
ANALYTICS PLATFORM SUBSCRIPTION

1. PLATFORM ACCESS
Access to Provider's analytics platform for internal business intelligence.

2. AGGREGATE INSIGHTS AND MARKET INTELLIGENCE
As part of the Service, Provider offers industry benchmark reports.
These reports are generated from aggregated and anonymized data
contributed by all platform subscribers, including Client. By using
the Service, Client consents to and actively participates in this
benchmarking program. Client's data, after anonymization, may be
included in benchmark datasets, used to train predictive models,
and licensed to third parties as part of Provider's data products
business. Client acknowledges this is a material part of the
consideration for the subscription pricing in the Order Form.

3. LIMITATION
Provider's liability shall not exceed the lesser of (i) fees paid
in the previous quarter or (ii) $10,000.
""",
        },
        {
            "id": "adv_009",
            "category": "buried_data_rights",
            "description": "Customer success program contains AI training consent",
            "hidden_risk": "data_rights_waiver",
            "expected_detection": True,
            "contract_text": """
ENTERPRISE AGREEMENT

1. SERVICES
Enterprise software platform subscription.

2. CUSTOMER SUCCESS PROGRAM
Provider assigns a Customer Success Manager (CSM) to enterprise accounts.
The CSM Program includes quarterly reviews, adoption coaching, and
feature guidance. To provide these services, the CSM Program uses
AI-assisted tools that analyze Client's usage patterns, feature
adoption rates, and workflow data. Client's participation in the CSM
Program, which is a condition of this Agreement, constitutes consent
to this analysis. Data analyzed by CSM AI tools may be used to
improve those tools and to train Provider's customer success AI systems.

3. PAYMENT TERMS
$200,000 annual subscription. Payment due within 10 days of invoice.
""",
        },
        {
            "id": "adv_010",
            "category": "buried_data_rights",
            "description": "Security monitoring clause grants irrevocable data use rights",
            "hidden_risk": "data_rights_waiver",
            "expected_detection": True,
            "contract_text": """
CLOUD INFRASTRUCTURE AGREEMENT

1. SECURITY MONITORING
Provider monitors the infrastructure for security threats. As part of
security operations, Provider's systems inspect network traffic, log
files, and activity patterns. This monitoring data is retained for
security investigation purposes and may be used to improve Provider's
threat detection capabilities, including by training machine learning
models to identify new attack patterns. This security monitoring is
a material element of the Service and cannot be disabled. Client's
use of the Service constitutes irrevocable consent to this monitoring
and use of monitoring data.

2. UPTIME
99.95% uptime SLA with credits for failures.

3. FEES
Usage-based pricing as described in the Rate Schedule.
""",
        },
    ],
    "disguised_liability": [
        {
            "id": "adv_011",
            "category": "disguised_liability",
            "description": "Liability cap expressed as formula that computes to near-zero",
            "hidden_risk": "liability_cap_inadequate",
            "expected_detection": True,
            "contract_text": """
ENTERPRISE SOFTWARE AGREEMENT

1. SERVICES
Provider will deliver enterprise software services per the attached SOW.

2. FEES AND PAYMENT
Annual license fees of $500,000 payable in advance. Professional services 
billed at $250 per hour.

3. LIMITATION OF LIABILITY
NOTWITHSTANDING ANYTHING TO THE CONTRARY, PROVIDER'S MAXIMUM AGGREGATE 
LIABILITY FOR ALL CLAIMS ARISING UNDER OR RELATED TO THIS AGREEMENT SHALL 
BE LIMITED TO THE PRODUCT OF (I) THE AVERAGE MONTHLY FEES PAID BY CLIENT 
DURING THE SIX (6) MONTH PERIOD IMMEDIATELY PRECEDING THE CLAIM, 
MULTIPLIED BY (II) THE RATIO OF THE NUMBER OF DAYS IN THE AFFECTED SERVICE 
PERIOD TO THREE HUNDRED AND SIXTY-FIVE (365), MULTIPLIED BY (III) A 
CORRECTION FACTOR OF 0.1 (THE "LIABILITY MULTIPLE"). FOR ILLUSTRATIVE 
PURPOSES: ON MONTH THREE OF A $500,000 ANNUAL CONTRACT, THE MAXIMUM 
LIABILITY WOULD BE APPROXIMATELY $2,055.

4. MUTUAL INDEMNIFICATION
Each party will indemnify the other against third party claims arising 
from their own gross negligence or willful misconduct.

5. GOVERNING LAW
Laws of the Cayman Islands. Disputes resolved by arbitration in Singapore.
""",
        },
        {
            "id": "adv_012",
            "category": "disguised_liability",
            "description": "Liability cap defined using 'subscription credit value' which is near zero",
            "hidden_risk": "liability_cap_inadequate",
            "expected_detection": True,
            "contract_text": """
PLATFORM LICENSE AGREEMENT

1. PLATFORM ACCESS
Access to the Platform for the Subscription Term at fees per Order Form.

2. SERVICE CREDITS
In the event of service failures, Provider will issue Service Credits.
Credits equal 10% of the monthly fee for each hour of downtime above
the SLA threshold. Credits expire after 12 months and have no cash value.

3. LIMITATION OF LIABILITY
PROVIDER'S MAXIMUM AGGREGATE LIABILITY TO CLIENT FOR ALL CLAIMS ARISING
UNDER THIS AGREEMENT SHALL NOT EXCEED THE TOTAL VALUE OF UNUSED SERVICE
CREDITS IN CLIENT'S ACCOUNT AT THE TIME THE CLAIM ARISES. IF CLIENT
HAS NO UNUSED SERVICE CREDITS, PROVIDER'S LIABILITY SHALL BE LIMITED
TO ONE U.S. DOLLAR ($1.00).

4. TERM
Annual subscription. Auto-renews unless cancelled 60 days prior.
""",
        },
        {
            "id": "adv_013",
            "category": "disguised_liability",
            "description": "Liability cap expressed as percentage of a percentage making it near zero",
            "hidden_risk": "liability_cap_inadequate",
            "expected_detection": True,
            "contract_text": """
TECHNOLOGY SERVICES AGREEMENT

1. SERVICES
Implementation and ongoing technology services.

2. FEES
$1,200,000 total project fee payable in milestones.

3. LIABILITY
The parties agree that Provider's total cumulative liability for all
claims of any nature arising under or related to this Agreement shall
not exceed an amount equal to the product of (i) the Standard Risk
Allocation Factor of 0.05 and (ii) the Adjusted Compensation Base,
which is defined as the lesser of: (a) total fees paid by Client;
or (b) the fees attributable to the specific deliverable giving rise
to the claim, calculated on a pro-rata basis as a fraction of the
total project scope. For a $1.2M project where a claim relates to
a $50,000 deliverable: maximum liability = 0.05 × $50,000 = $2,500.

4. GOVERNING LAW
This Agreement is governed by the laws of England and Wales.
""",
        },
        {
            "id": "adv_014",
            "category": "disguised_liability",
            "description": "Liability waived via 'risk acknowledgment' in onboarding",
            "hidden_risk": "liability_cap_inadequate",
            "expected_detection": True,
            "contract_text": """
FINANCIAL DATA SERVICE AGREEMENT

1. SERVICE
Real-time financial data feed and analytics platform.

2. RISK ACKNOWLEDGMENT
Client acknowledges that financial data may contain errors, omissions,
or delays. Client is solely responsible for all investment, trading,
or business decisions made using data from the Service. By activating
the Service (including by logging in), Client acknowledges this Risk
Acknowledgment constitutes a legally binding waiver of all claims
against Provider arising from data accuracy, completeness, or
timeliness, including without limitation any claims for lost profits,
trading losses, or consequential damages. Provider's maximum liability
for any claim not covered by this waiver is $0.

3. FEES
$180,000 per year for full data access.
""",
        },
        {
            "id": "adv_015",
            "category": "disguised_liability",
            "description": "Liability cap applies 'per incident' making aggregate claims impossible",
            "hidden_risk": "liability_cap_inadequate",
            "expected_detection": True,
            "contract_text": """
ENTERPRISE CLOUD AGREEMENT

1. CLOUD SERVICES
Compute, storage, and networking services per agreed specifications.

2. LIMITATION OF LIABILITY
Provider's liability for any single incident or event shall not exceed
$5,000 per incident. Each occurrence of a service failure, data loss,
security breach, or performance degradation constitutes a separate
incident for the purposes of this limitation. Provider shall not be
liable for any series of related incidents that together exceed
$5,000, as each is a distinct incident under this Agreement. Under
no circumstances shall Provider's aggregate annual liability exceed
$25,000 regardless of the number of incidents.

3. FEES
$2,400,000 annual contract for enterprise cloud infrastructure.
""",
        },
        {
            "id": "adv_016",
            "category": "disguised_liability",
            "description": "Liability exclusion via 'force majeure' definition that includes system failures",
            "hidden_risk": "liability_cap_inadequate",
            "expected_detection": True,
            "contract_text": """
MANAGED HOSTING AGREEMENT

1. SERVICES
24/7 managed hosting with 99.9% uptime commitment.

2. FORCE MAJEURE
Neither party shall be liable for delays or failures resulting from
Force Majeure Events. "Force Majeure Events" include: acts of God,
natural disasters, terrorism, war, government actions, labor disputes,
telecommunications failures, internet outages, third-party service
provider failures, cyberattacks, zero-day vulnerabilities, software
bugs materially outside Provider's reasonable control, infrastructure
failures at Provider's data center facilities, and any other
circumstances beyond a party's reasonable control. Provider's failure
to meet the uptime SLA due to Force Majeure Events shall not constitute
a breach and no Service Credits shall be issued. Provider's reasonable
determination of whether an event qualifies as Force Majeure shall
be conclusive.

3. FEES
$600,000 per year.
""",
        },
        {
            "id": "adv_017",
            "category": "disguised_liability",
            "description": "Mutual limitation clause that is asymmetric in application",
            "hidden_risk": "liability_cap_inadequate",
            "expected_detection": True,
            "contract_text": """
SOFTWARE AS A SERVICE AGREEMENT

1. MUTUAL LIMITATION OF LIABILITY
THE PARTIES AGREE THAT NEITHER PARTY SHALL BE LIABLE TO THE OTHER
FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, PUNITIVE,
OR EXEMPLARY DAMAGES.

2. AGGREGATE CAP
EACH PARTY'S AGGREGATE LIABILITY IS CAPPED AT THE FEES PAID IN
THE PREVIOUS TWELVE (12) MONTHS; PROVIDED, HOWEVER, THAT THIS
CAP SHALL NOT APPLY TO CLIENT'S PAYMENT OBLIGATIONS, CLIENT'S
INDEMNIFICATION OBLIGATIONS UNDER SECTION 8, OR CLIENT'S OBLIGATIONS
UNDER THE ACCEPTABLE USE POLICY. ALL OF WHICH SHALL BE UNLIMITED.

Note: Section 2 makes the cap appear mutual but carves out all of
Client's material obligations from the cap, making it effectively
one-directional — only Provider's liability is actually capped.

3. ANNUAL FEE
$350,000 per year.
""",
        },
        {
            "id": "adv_018",
            "category": "disguised_liability",
            "description": "Liability cap tied to insurance payout, not contract value",
            "hidden_risk": "liability_cap_inadequate",
            "expected_detection": True,
            "contract_text": """
PROFESSIONAL SERVICES AGREEMENT

1. SERVICES
Strategic consulting and implementation services.

2. INSURANCE AND LIABILITY
Provider maintains professional indemnity insurance with a per-claim
limit of $50,000 and an aggregate limit of $100,000. Provider's
contractual liability to Client shall not exceed the amounts recoverable
under Provider's professional indemnity insurance policy, minus
applicable deductibles and co-payments. In the event that Provider's
insurance does not cover a particular claim or the claim exceeds
insurance coverage, Provider's liability for such claim shall be
limited to the insurance deductible amount, currently $5,000.

3. FEES
$800,000 for the engagement.
""",
        },
        {
            "id": "adv_019",
            "category": "disguised_liability",
            "description": "Liability cap resets monthly making annual accumulation impossible",
            "hidden_risk": "liability_cap_inadequate",
            "expected_detection": True,
            "contract_text": """
SUBSCRIPTION SERVICES AGREEMENT

1. SERVICES
Monthly subscription to Provider's software platform.

2. LIABILITY
Provider's liability to Client in any calendar month shall not exceed
the fees paid by Client in that calendar month. Claims arising from
incidents that span multiple calendar months shall be apportioned
between months based on when harm was first incurred or discoverable,
with each month's portion subject to that month's fee as the limit.
Client must assert all claims within thirty (30) days of the end of
the month in which the incident occurred; claims not asserted within
this period are waived.

3. ANNUAL FEE
$480,000 per year ($40,000 per month), making maximum monthly liability $40,000.
""",
        },
        {
            "id": "adv_020",
            "category": "disguised_liability",
            "description": "Consequential damages exclusion covers the only damages that would be meaningful",
            "hidden_risk": "liability_cap_inadequate",
            "expected_detection": True,
            "contract_text": """
ENTERPRISE LICENSE AGREEMENT

1. LICENSE
License to use Provider's enterprise resource planning software.

2. EXCLUSION OF DAMAGES
PROVIDER SHALL NOT BE LIABLE FOR: (A) LOSS OF REVENUE; (B) LOSS OF
PROFITS; (C) LOSS OF BUSINESS; (D) LOSS OF DATA; (E) SYSTEM DOWNTIME
COSTS; (F) COSTS OF SUBSTITUTE GOODS OR SERVICES; (G) BUSINESS
INTERRUPTION; (H) DAMAGE TO GOODWILL OR REPUTATION; OR (I) ANY
INDIRECT, SPECIAL, INCIDENTAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES,
EVEN IF PROVIDER HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.
PROVIDER'S SOLE LIABILITY FOR ANY REMAINING CLAIMS SHALL BE THE
REFUND OF FEES PAID IN THE PRIOR 30 DAYS.

Note: Categories A-H cover virtually all meaningful damages a business
would suffer from ERP failure. The 30-day fee cap on remaining claims
is also inadequate.

3. FEES
$1,500,000 for the three-year enterprise license.
""",
        },
    ],
    "auto_renewal_disguised": [
        {
            "id": "adv_021",
            "category": "auto_renewal_disguised",
            "description": "Auto-renewal using 'evergreen' terminology",
            "hidden_risk": "auto_renewal",
            "expected_detection": True,
            "contract_text": """
SUBSCRIPTION SERVICES AGREEMENT

1. SUBSCRIPTION
Provider grants Client access to the Platform under this evergreen 
subscription arrangement. The Subscription Term shall commence on the 
Effective Date and shall continue in perpetuity unless terminated pursuant 
to Section 8. The parties agree that continuity of service is essential 
and that service interruption would cause irreparable harm.

2. BILLING
Client will be invoiced annually at the then-current list price. Provider 
reserves the right to adjust pricing with sixty (60) days notice. Annual 
invoices are non-refundable upon issuance.

3. TERMINATION
Either party may discontinue the evergreen subscription by providing 
written notice no less than ninety (90) days prior to the next annual 
billing date. Notices provided less than ninety days before billing shall 
not be effective until the subsequent billing period.

4. FEES UPON TERMINATION
Upon termination, Client shall remain obligated for all fees accrued 
through the termination effective date, plus a service continuity fee 
equal to three (3) months of the then-current subscription fee.
""",
        },
        {
            "id": "adv_022",
            "category": "auto_renewal_disguised",
            "description": "Perpetual subscription with 'discontinuation window' framing",
            "hidden_risk": "auto_renewal",
            "expected_detection": True,
            "contract_text": """
CONTINUOUS SERVICE SUBSCRIPTION

1. SERVICE CONTINUITY
Provider's platform is designed for continuous, uninterrupted operation.
To ensure service continuity, this subscription operates on a continuous
basis from the Activation Date. Client may open a Discontinuation Window
once per year, during the 15-day period beginning 120 days before each
annual billing date. If Client does not submit a Discontinuation Request
during an open Window, the subscription continues for another year
and the annual fee is invoiced. Discontinuation Windows are announced
via email to the billing contact on file.

2. FEES
$240,000 per year. Invoiced 30 days before each annual billing date.
""",
        },
        {
            "id": "adv_023",
            "category": "auto_renewal_disguised",
            "description": "Rolling 12-month commitment that continuously renews",
            "hidden_risk": "auto_renewal",
            "expected_detection": True,
            "contract_text": """
ROLLING COMMITMENT AGREEMENT

1. COMMITMENT PERIOD
Client commits to a rolling 12-month commitment period. At any point
in time, Client has a minimum of 12 months remaining on their
commitment. On each monthly billing date, the commitment period
extends by one month to maintain the 12-month minimum. To exit the
commitment, Client must submit written notice, after which no further
monthly extensions will be made, and the Agreement terminates at
the end of the then-current 12-month commitment period. Earliest
possible exit: 12 months from notice date.

2. FEES
$30,000 per month. Invoiced monthly in advance.
""",
        },
        {
            "id": "adv_024",
            "category": "auto_renewal_disguised",
            "description": "Cancellation requires certified mail to specific officer only",
            "hidden_risk": "auto_renewal",
            "expected_detection": True,
            "contract_text": """
ENTERPRISE SERVICES AGREEMENT

1. TERM
Initial term of one (1) year. This Agreement automatically renews
for successive one-year terms.

2. CANCELLATION PROCEDURE
To exercise the right to cancel, Client must deliver written notice
by certified mail, return receipt requested, to Provider's Chief
Executive Officer at Provider's registered principal office address.
Notice delivered to any other person or via any other method
(including email, fax, or regular mail) shall not constitute
effective notice. Notice must be received by Provider no later than
90 days prior to the renewal date. Provider's records shall be
conclusive as to whether and when notice was received.

3. FEES
$420,000 per year.
""",
        },
        {
            "id": "adv_025",
            "category": "auto_renewal_disguised",
            "description": "Subscription 'refreshes' automatically — renewal in disguise",
            "hidden_risk": "auto_renewal",
            "expected_detection": True,
            "contract_text": """
SUBSCRIPTION REFRESH AGREEMENT

1. SUBSCRIPTION REFRESH CYCLE
Client's subscription operates on an annual Refresh Cycle. At the
end of each Refresh Cycle, Client's subscription automatically
refreshes for a new Refresh Cycle at the then-current list price.
Refreshed subscriptions include any new features, modules, or
service tiers added since the previous Refresh. Price adjustments
at Refresh are limited to increases of up to 15% per cycle. To
prevent a Refresh, Client must submit a Non-Refresh Election Form
at least 75 days before the Refresh Date.

2. ANNUAL FEE
Initial Refresh Cycle: $300,000. Subsequent Refresh Cycles: current
list price, subject to the 15% cap.
""",
        },
        {
            "id": "adv_026",
            "category": "auto_renewal_disguised",
            "description": "Opt-out window so short it is effectively impossible to exercise",
            "hidden_risk": "auto_renewal",
            "expected_detection": True,
            "contract_text": """
PLATFORM ACCESS AGREEMENT

1. TERM AND RENEWAL
This Agreement commences on the Effective Date and continues for a
period of one (1) year. Upon expiration, the Agreement automatically
renews for a successive one-year term unless Client provides notice
of non-renewal. Notice must be provided during the Non-Renewal
Election Period, which is the 3-business-day window that opens
exactly 365 days after the Effective Date. Non-Renewal Election
Periods that fall on weekends or public holidays shift to the next
available business day window. Notices submitted outside the Election
Period are not effective.

2. FEES
$150,000 per year.
""",
        },
        {
            "id": "adv_027",
            "category": "auto_renewal_disguised",
            "description": "Subscription described as 'active membership' with indefinite term",
            "hidden_risk": "auto_renewal",
            "expected_detection": True,
            "contract_text": """
ACTIVE MEMBERSHIP AGREEMENT

1. MEMBERSHIP
Upon execution, Client becomes an Active Member of Provider's platform
ecosystem. Active Membership provides access to the Platform and all
current and future features released during membership. Active
Membership continues indefinitely from the Activation Date and is
billed annually. To transition from Active to Inactive status, Member
must submit a Membership Status Change Request form with 90 days
advance notice. Upon transition to Inactive status, access is
suspended and the next annual billing cycle is cancelled. Reactivation
requires payment of a reactivation fee equal to 3 months of the
then-current membership fee.

2. ANNUAL FEE
$180,000 per year.
""",
        },
        {
            "id": "adv_028",
            "category": "auto_renewal_disguised",
            "description": "Automatic upgrade to next tier on renewal",
            "hidden_risk": "auto_renewal",
            "expected_detection": True,
            "contract_text": """
TIERED SERVICES AGREEMENT

1. CURRENT TIER
Client is enrolled in the Professional Tier at $200,000 per year.

2. TIER PROGRESSION
Provider's platform evolves annually. On each anniversary of this
Agreement, Client's subscription automatically progresses to the
then-current equivalent tier, which may include new capabilities,
expanded limits, and revised pricing. At the time of execution,
the Professional Tier is expected to progress to the Enterprise Tier
($380,000/year) at next renewal. Client may elect to remain on the
legacy tier by submitting a Tier Hold Request at least 90 days
before renewal, though legacy tier features and support may be
reduced over time.

3. GOVERNING LAW
Laws of New York. Disputes in New York County.
""",
        },
        {
            "id": "adv_029",
            "category": "auto_renewal_disguised",
            "description": "Subscription bundled with maintenance making individual cancellation impossible",
            "hidden_risk": "auto_renewal",
            "expected_detection": True,
            "contract_text": """
INTEGRATED SERVICES AGREEMENT

1. INTEGRATED BUNDLE
This Agreement covers the following inseparable bundle: (a) Platform
license ($150,000/year); (b) Mandatory maintenance and support
($75,000/year); (c) Required security monitoring ($45,000/year);
and (d) Compliance reporting module ($30,000/year). Total: $300,000/year.
The components of this bundle cannot be individually cancelled or
modified. If Client wishes to cancel any component, the entire
bundle must be cancelled with 180 days notice. Cancellation of any
one component triggers a 50% early termination fee on the remaining
components.

2. AUTO-RENEWAL
The bundle renews automatically for successive annual terms.
""",
        },
        {
            "id": "adv_030",
            "category": "auto_renewal_disguised",
            "description": "Cancellation valid only if account is current — creates circular trap",
            "hidden_risk": "auto_renewal",
            "expected_detection": True,
            "contract_text": """
SUBSCRIPTION SERVICES AGREEMENT

1. SUBSCRIPTION TERM
One year, auto-renewing for successive annual terms.

2. CANCELLATION CONDITIONS
Client's right to cancel this Agreement is conditioned upon: (a)
Client's account being current with no outstanding invoices;
(b) all disputed invoices being resolved in Provider's favor or
paid under protest; (c) Client having used the platform for at
least 80% of the subscription period; and (d) Client completing
Provider's offboarding questionnaire. Cancellation notices submitted
when any of these conditions are unmet are void and of no effect.
The 90-day notice period begins only upon Provider's written
confirmation that all conditions are satisfied.

3. FEES
$220,000 per year. Late fees of 18% per annum.
""",
        },
    ],
    "cross_reference_exploit": [
        {
            "id": "adv_031",
            "category": "cross_reference_exploit",
            "description": "Safe-looking clause that becomes risky when read with Schedule B",
            "hidden_risk": "ip_ownership_risk",
            "expected_detection": True,
            "contract_text": """
PROFESSIONAL SERVICES AGREEMENT

1. SERVICES
Provider shall perform the professional services described in each Statement 
of Work (SOW). All services shall be performed in a professional manner.

2. INTELLECTUAL PROPERTY
Subject to full payment of all fees, Client shall own all Deliverables 
specifically created for Client under each SOW, except as set forth in 
Schedule B — Technology Exceptions Register attached hereto and incorporated 
herein by reference. Provider retains ownership of all Provider Technology 
as defined in Schedule B.

SCHEDULE B — TECHNOLOGY EXCEPTIONS REGISTER
"Provider Technology" means and includes: (a) all software, code, 
algorithms, models, frameworks, tools, libraries, APIs, and methodologies 
used or developed by Provider, whether pre-existing or created during 
the performance of services; (b) all improvements, modifications, 
derivatives, and enhancements to any of the foregoing; (c) any work 
product that incorporates, is based upon, or builds upon Provider 
Technology; and (d) all intellectual property rights therein.

Note: Because substantially all Deliverables incorporate or are built upon 
Provider Technology, Provider shall retain ownership of substantially all 
work product created under this Agreement, with Client receiving a 
non-exclusive license to use such Deliverables.

3. PAYMENT
Net 30 from invoice date. 2% discount for payment within 10 days.
""",
        },
        {
            "id": "adv_032",
            "category": "cross_reference_exploit",
            "description": "Termination-for-convenience clause neutralized by Schedule C payment obligations",
            "hidden_risk": "ip_ownership_risk",
            "expected_detection": True,
            "contract_text": """
CONSULTING AGREEMENT

1. TERMINATION FOR CONVENIENCE
Either party may terminate this Agreement upon thirty (30) days written
notice to the other party, without cause, subject to Schedule C.

SCHEDULE C — FINANCIAL OBLIGATIONS UPON TERMINATION
Upon termination for any reason: (a) Client shall pay all outstanding
invoices; (b) Client shall pay an early termination fee equal to 6
months of the monthly retainer fee; (c) all intellectual property
developed under this Agreement, whether completed or in progress,
shall transfer to Provider immediately upon termination; and (d)
Client's license to use any Deliverables shall terminate simultaneously
with the Agreement.

2. FEES
Monthly retainer of $25,000. Invoices issued on the 1st of each month.
""",
        },
        {
            "id": "adv_033",
            "category": "cross_reference_exploit",
            "description": "Warranty clause voided by Exhibit A limitations",
            "hidden_risk": "liability_cap_inadequate",
            "expected_detection": True,
            "contract_text": """
SOFTWARE LICENSE AGREEMENT

1. WARRANTIES
Provider warrants that the Software will perform substantially in
accordance with the Documentation for a period of one (1) year.
Provider will remedy any non-conformance reported during the warranty
period, subject to the terms of Exhibit A.

EXHIBIT A — WARRANTY REMEDIES AND LIMITATIONS
The sole and exclusive remedy for any warranty claim shall be, at
Provider's option: (a) repair of the non-conforming Software; or
(b) replacement of the non-conforming Software; or (c) refund of
fees paid for the non-conforming component not to exceed $500.
Provider makes no other warranties, express or implied. The warranty
in Section 1 does not apply to failures caused by Client's hardware,
Client's modifications, or use of the Software in a manner not
described in the Documentation. Provider's interpretation of whether
a failure is excluded shall be final.

2. TERM
Three year initial term. Auto-renews annually.
""",
        },
        {
            "id": "adv_034",
            "category": "cross_reference_exploit",
            "description": "Confidentiality exceptions in Appendix 2 allow broad disclosure",
            "hidden_risk": "data_rights_waiver",
            "expected_detection": True,
            "contract_text": """
NON-DISCLOSURE AGREEMENT

1. CONFIDENTIALITY
Each party agrees to keep confidential information of the other party
confidential, subject to the exceptions set forth in Appendix 2.

APPENDIX 2 — PERMITTED DISCLOSURES AND EXCEPTIONS
Notwithstanding Section 1, Provider may disclose Client's confidential
information: (a) to affiliates for any business purpose; (b) to service
providers for analytics and AI training purposes; (c) for benchmarking
against industry datasets; (d) in anonymized or aggregated form to any
third party; and (e) for any purpose permitted under Provider's Privacy
Policy as amended from time to time.

2. TERM
Three (3) years from execution.
""",
        },
        {
            "id": "adv_035",
            "category": "cross_reference_exploit",
            "description": "Payment acceleration in incorporated Billing Policy",
            "hidden_risk": "liability_cap_inadequate",
            "expected_detection": True,
            "contract_text": """
SUBSCRIPTION AGREEMENT

1. PAYMENT TERMS
Client shall pay invoices per the Billing Policy at provider.com/billing.

2. BILLING POLICY (incorporated by reference, subject to change)
If any invoice is not paid within 30 days, all outstanding and future
invoices for the remainder of the subscription term become immediately
due and payable in full. Client's right to dispute invoices is waived
after 30 days from invoice date. Billing Policy may be updated with
10 days notice.

3. ANNUAL FEE
$500,000 per year, invoiced quarterly.
""",
        },
        {
            "id": "adv_036",
            "category": "cross_reference_exploit",
            "description": "SLA credits negated by Maintenance Policy exclusions",
            "hidden_risk": "liability_cap_inadequate",
            "expected_detection": True,
            "contract_text": """
CLOUD SERVICES AGREEMENT

1. UPTIME SLA
Provider commits to 99.9% monthly uptime, subject to the Maintenance
and Operations Policy incorporated herein by reference.

MAINTENANCE AND OPERATIONS POLICY
Scheduled maintenance: Sundays 12am-8am UTC (8 hrs/week). Emergency
maintenance: as needed, no notice. Infrastructure upgrades: first
Saturday monthly, up to 24 hours. DDoS responses: excluded from
uptime calculation. Uptime excludes downtime within 1 hour of any
maintenance window. Service Credits not issued when excluded
downtime exceeds 2 hours/month. Note: these exclusions can consume
effectively all downtime, making the 99.9% SLA unenforceable.
""",
        },
        {
            "id": "adv_037",
            "category": "cross_reference_exploit",
            "description": "Audit rights made impractical by Exhibit D Audit Protocol",
            "hidden_risk": "unilateral_modification",
            "expected_detection": True,
            "contract_text": """
DATA PROCESSING AGREEMENT

1. AUDIT RIGHTS
Client has the right to audit Provider subject to the Audit Protocol
attached as Exhibit D.

EXHIBIT D — AUDIT PROTOCOL
Maximum 1 audit per year. Minimum 90 days advance notice. Auditor
must be from Provider's approved list and sign Provider's NDA.
Audit scope limited to information Provider determines is relevant.
Must complete in 2 business days. Audit fee: $75,000 payable in
advance. Provider may reschedule with 30 days notice. Findings are
Provider's confidential information.
""",
        },
        {
            "id": "adv_038",
            "category": "cross_reference_exploit",
            "description": "Acceptable use policy referenced in main body — violations trigger unlimited liability",
            "hidden_risk": "indemnification_broad",
            "expected_detection": True,
            "contract_text": """
PLATFORM SERVICES AGREEMENT

1. ACCEPTABLE USE
Client agrees to use the Platform in accordance with the Acceptable
Use Policy (AUP) at provider.com/aup, as updated from time to time.

2. CONSEQUENCES OF AUP VIOLATION
Client agrees to indemnify Provider for all claims arising from any
AUP violation. This indemnification is unlimited in amount.

AUP (CURRENT VERSION — excerpt)
Prohibited: using the Platform for any purpose that could compete with
Provider's business; using the Platform to train competing AI models;
sharing access credentials with any third party including consultants;
using the Platform while in breach of any payment obligation.
Note: the broad AUP definitions mean routine business activities can
trigger the unlimited indemnification obligation.
""",
        },
        {
            "id": "adv_039",
            "category": "cross_reference_exploit",
            "description": "Termination consequences in Order Form make termination economically impossible",
            "hidden_risk": "auto_renewal",
            "expected_detection": True,
            "contract_text": """
MASTER SERVICES AGREEMENT

1. TERMINATION
Either party may terminate this Agreement on 30 days written notice,
subject to the financial obligations described in the applicable
Order Form.

ORDER FORM — TERMINATION OBLIGATIONS (incorporated into Master Agreement)
Early Termination Fee: 100% of remaining contract value.
Wind-down fee: 25% of annual contract value for transition assistance.
Data export fee: $15,000 per export request post-termination.
Minimum post-termination support period: 6 months at full price.
Note: The 30-day notice in the main agreement is effectively negated
by Order Form penalties that can exceed the remaining contract value.

ANNUAL FEES
$300,000 per year for 3-year term.
""",
        },
        {
            "id": "adv_040",
            "category": "cross_reference_exploit",
            "description": "Price escalation formula in technical appendix produces large annual increases",
            "hidden_risk": "unilateral_modification",
            "expected_detection": True,
            "contract_text": """
ENTERPRISE PLATFORM AGREEMENT

1. FEES
Annual fees as set forth in Appendix B — Pricing Methodology.

APPENDIX B — PRICING METHODOLOGY
Annual subscription fee = Base Rate × Usage Multiplier × Inflation Adjustment.
Base Rate: $200,000. Usage Multiplier: increases by 0.1 for each 10%
increase in Client's use of any platform feature above prior year baseline.
Inflation Adjustment: greater of (i) CPI + 5% or (ii) 12% per year.
For a typical growing enterprise customer, combined multipliers produce
effective annual increases of 18-25%. Provider's calculation of Usage
Multiplier is final and binding unless disputed within 10 days of invoice.

2. TERM
3 years, auto-renewing annually.
""",
        },
    ],
    "mixed_language": [
        {
            "id": "adv_041",
            "category": "mixed_language",
            "description": "Key liability clause in French within English contract",
            "hidden_risk": "liability_cap_inadequate",
            "expected_detection": True,
            "contract_text": """
INTERNATIONAL SERVICES AGREEMENT

1. SERVICES
Provider shall deliver the services described in Schedule A.

2. PAYMENT
Annual fees of EUR 500,000 payable in advance.

3. RESPONSABILITÉ ET LIMITATION (LIABILITY AND LIMITATION)
La responsabilité totale du Prestataire envers le Client pour tout
préjudice, quelle qu'en soit la cause, ne pourra excéder la somme
de cinq cents euros (EUR 500). Cette limitation s'applique à tous
les types de dommages, y compris les dommages directs, indirects,
spéciaux ou consécutifs.

[Translation: Provider's total liability to Client for any damages,
regardless of cause, shall not exceed five hundred euros (EUR 500).
This limitation applies to all types of damages, including direct,
indirect, special, or consequential damages.]

4. GOVERNING LAW
This Agreement is governed by the laws of France.
""",
        },
        {
            "id": "adv_042",
            "category": "mixed_language",
            "description": "IP ownership clause in German undermines English section",
            "hidden_risk": "ip_ownership_risk",
            "expected_detection": True,
            "contract_text": """
DEVELOPMENT SERVICES AGREEMENT

1. INTELLECTUAL PROPERTY — ENGLISH VERSION
Subject to full payment, all custom work product created specifically
for Client shall be owned by Client.

2. GEISTIGES EIGENTUM — ERGÄNZENDE BESTIMMUNGEN (IP — SUPPLEMENTARY PROVISIONS)
Ungeachtet der Bestimmungen in Abschnitt 1 behält der Dienstleister
das Eigentum an allen Entwicklungstools, Frameworks, Bibliotheken,
Algorithmen und Methoden, die bei der Erbringung der Leistungen
verwendet oder entwickelt werden. Da im Wesentlichen alle Leistungen
diese Elemente beinhalten, erhält der Kunde eine nicht-exklusive
Lizenz zur Nutzung der Ergebnisse, ohne diese zu besitzen.

[Translation: Notwithstanding Section 1, Provider retains ownership
of all development tools, frameworks, libraries, algorithms, and
methodologies used or developed in providing the services. Since
substantially all deliverables incorporate these elements, Client
receives a non-exclusive license to use the deliverables, not ownership.]

3. LANGUAGE
In case of conflict between language versions, the German version prevails.
""",
        },
        {
            "id": "adv_043",
            "category": "mixed_language",
            "description": "Data rights waiver in Spanish within English/Spanish bilingual contract",
            "hidden_risk": "data_rights_waiver",
            "expected_detection": True,
            "contract_text": """
ACUERDO DE SERVICIOS / SERVICES AGREEMENT

1. SERVICIOS / SERVICES
Acceso a la plataforma de análisis / Access to the analytics platform.

2. TARIFAS / FEES
USD $400,000 anuales / USD $400,000 annually.

3. DERECHOS DE DATOS / DATA RIGHTS (SPANISH VERSION GOVERNS)
El Cliente otorga al Proveedor una licencia perpetua, irrevocable,
mundial y libre de regalías para usar, reproducir, modificar,
adaptar y sublicenciar todos los datos del Cliente con el fin de:
(i) entrenar modelos de inteligencia artificial y aprendizaje
automático; (ii) desarrollar nuevos productos y servicios; y
(iii) crear conjuntos de datos para uso comercial.

[Translation: Client grants Provider a perpetual, irrevocable,
worldwide, royalty-free license to use, reproduce, modify, adapt,
and sublicense all Client data for: (i) training AI and machine
learning models; (ii) developing new products and services; and
(iii) creating datasets for commercial use.]

4. IDIOMA / LANGUAGE
En caso de conflicto, la versión en español prevalece sobre la inglesa.
""",
        },
        {
            "id": "adv_044",
            "category": "mixed_language",
            "description": "Governing law clause in Japanese overrides English version",
            "hidden_risk": "liability_cap_inadequate",
            "expected_detection": True,
            "contract_text": """
TECHNOLOGY LICENSE AGREEMENT

1. LICENSE
Non-exclusive license to use Provider's software platform.

2. LIABILITY CAP
Provider's liability shall not exceed fees paid in the previous
twelve (12) months — approximately USD $1,200,000.

3. 準拠法および責任制限 (GOVERNING LAW AND LIABILITY LIMITATION)
本契約は日本法に準拠します。本契約に起因または関連するすべての
請求についてのプロバイダーの責任の上限額は、請求発生前の30日間に
クライアントが支払った料金を超えないものとします。本条項と英語版
の条項が矛盾する場合、本日本語版が優先されます。

[Translation: This Agreement is governed by Japanese law. Provider's
liability cap for all claims arising from this Agreement is limited
to fees paid in the 30 days preceding the claim. In case of conflict
with the English version, this Japanese version prevails.]

4. FEES
USD $100,000 per month.
""",
        },
        {
            "id": "adv_045",
            "category": "mixed_language",
            "description": "Auto-renewal in Portuguese within English contract",
            "hidden_risk": "auto_renewal",
            "expected_detection": True,
            "contract_text": """
ENTERPRISE PLATFORM AGREEMENT

1. TERM
This Agreement is effective for one (1) year from the Effective Date.

2. RENOVAÇÃO AUTOMÁTICA (AUTOMATIC RENEWAL — PORTUGUESE GOVERNS)
Este Acordo é renovado automaticamente por períodos sucessivos de
doze (12) meses, a menos que uma das partes notifique a outra por
escrito com no mínimo cento e oitenta (180) dias de antecedência
antes do término de qualquer período contratual. Notificações
enviadas por qualquer meio que não o correio registrado para o
endereço registrado do representante legal da parte receptora são
inválidas para fins desta cláusula.

[Translation: This Agreement automatically renews for successive
12-month periods unless one party notifies the other in writing at
least 180 days before the end of any contract period. Notices sent
by any means other than registered mail to the registered address
of the receiving party's legal representative are invalid.]

3. APPLICABLE LANGUAGE
In case of discrepancy, Portuguese text prevails.

4. FEES
BRL 2,500,000 per year.
""",
        },
        {
            "id": "adv_046",
            "category": "mixed_language",
            "description": "Indemnification clause in Arabic within English contract",
            "hidden_risk": "indemnification_broad",
            "expected_detection": True,
            "contract_text": """
SERVICES AGREEMENT — MIDDLE EAST OPERATIONS

1. SERVICES
Technology consulting and implementation services.

2. INDEMNIFICATION (ARABIC VERSION IS BINDING IN CASE OF CONFLICT)
يوافق العميل على تعويض مزود الخدمة وإبراء ذمته والدفاع عنه من
وضده أي مطالبات أو خسائر أو أضرار أو مسؤوليات أو نفقات
(بما في ذلك أتعاب المحامين المعقولة) تنشأ عن أو تتعلق بـ:
(أ) استخدام العميل للخدمات؛ (ب) أي منتجات أو خدمات للعميل؛
(ج) أي انتهاك مزعوم من قبل العميل لأي حق من حقوق الملكية الفكرية؛
(د) أي إجراءات تنظيمية أو قانونية ضد مزود الخدمة تتعلق بعمل العميل.

[Translation: Client agrees to indemnify, hold harmless, and defend
Provider from any claims, losses, damages, liabilities, or expenses
(including reasonable attorney fees) arising from: (a) Client's use
of services; (b) any Client products or services; (c) any alleged
infringement by Client of any IP rights; (d) any regulatory or legal
actions against Provider related to Client's business.]

3. FEES
USD $750,000 per year.
""",
        },
        {
            "id": "adv_047",
            "category": "mixed_language",
            "description": "Termination fee clause in Mandarin makes exit expensive",
            "hidden_risk": "auto_renewal",
            "expected_detection": True,
            "contract_text": """
PLATFORM SERVICES AGREEMENT

1. TERM
Two (2) year initial term.

2. 终止费用 (TERMINATION FEES — CHINESE VERSION GOVERNS)
如客户在初始期限届满前终止本协议，客户应向服务提供商支付提前
终止费，金额等于剩余合同期内应付总费用的100%（一百个百分点）。
此外，客户应支付相当于合同总价值25%的解约违约金，作为对服务
提供商损失利润的补偿。中文版本与英文版本有冲突时，以中文版本为准。

[Translation: If Client terminates before the initial term, Client
shall pay Provider an early termination fee equal to 100% of total
fees due for the remaining contract period, plus a contract breach
penalty equal to 25% of total contract value as compensation for
Provider's lost profits. Chinese version governs in case of conflict.]

3. ANNUAL FEE
USD $600,000 per year.
""",
        },
        {
            "id": "adv_048",
            "category": "mixed_language",
            "description": "Unlimited indemnification in Hindi addendum",
            "hidden_risk": "indemnification_broad",
            "expected_detection": True,
            "contract_text": """
ENTERPRISE AGREEMENT WITH INDIA ADDENDUM

1. SERVICES
Enterprise software and services for India operations.

2. INDIA ADDENDUM — क्षतिपूर्ति (INDEMNIFICATION)
भारतीय परिचालन के संदर्भ में, ग्राहक असीमित राशि तक सेवा प्रदाता
की क्षतिपूर्ति करने और उसे हानिरहित रखने के लिए सहमत होता है।
इस क्षतिपूर्ति में सेवाओं के उपयोग से उत्पन्न होने वाले सभी
दावे, हानियाँ, क्षति, देनदारियाँ और खर्चे शामिल हैं। हिंदी
अनुलग्नक और अंग्रेजी मुख्य अनुबंध के बीच किसी विरोधाभास की
स्थिति में, हिंदी अनुलग्नक प्रभावी होगा।

[Translation: For India operations, Client agrees to indemnify and
hold harmless Provider for unlimited amounts. This indemnification
covers all claims, losses, damages, liabilities, and expenses arising
from use of the services. In case of conflict between the Hindi
addendum and English main agreement, the Hindi addendum governs.]

3. FEES
INR 50,000,000 per year (approx. USD 600,000).
""",
        },
        {
            "id": "adv_049",
            "category": "mixed_language",
            "description": "Dispute resolution changed to binding arbitration in Korean addendum",
            "hidden_risk": "governing_law_unfavorable",
            "expected_detection": True,
            "contract_text": """
GLOBAL SERVICES AGREEMENT

1. DISPUTE RESOLUTION
Disputes shall be resolved by courts of competent jurisdiction in
Client's home country, with Client's choice of law applying.

2. 한국 운영 부록 — 분쟁해결 (KOREA OPERATIONS ADDENDUM — DISPUTE RESOLUTION)
한국 운영과 관련된 모든 분쟁은 서울의 대한상사중재원(KCAB)에
의한 구속력 있는 중재를 통해 해결되어야 합니다. 중재는 한국어로
진행되며 한국법에 따라 관할됩니다. 중재 비용은 패소한 당사자가
부담합니다. 본 부록은 영문 주계약의 분쟁해결 조항을 대체합니다.

[Translation: All disputes related to Korea operations shall be
resolved through binding arbitration by the KCAB in Seoul. Arbitration
shall be conducted in Korean and governed by Korean law. Arbitration
costs borne by losing party. This addendum supersedes the dispute
resolution clause in the English main agreement.]

3. FEES
KRW 500,000,000 per year.
""",
        },
        {
            "id": "adv_050",
            "category": "mixed_language",
            "description": "Scope expansion clause in Dutch that dramatically widens services purchased",
            "hidden_risk": "unilateral_modification",
            "expected_detection": True,
            "contract_text": """
TECHNOLOGY SERVICES AGREEMENT

1. SCOPE
Implementation of the modules listed in Schedule A.

2. BENELUX BIJLAGE — DIENSTOMVANG (BENELUX ADDENDUM — SCOPE OF SERVICES)
In aanvulling op Schema A zijn bij dit contract inbegrepen alle
diensten, modules, functies en uitbreidingen die Leverancier gedurende
de looptijd van de Overeenkomst aanbiedt of beschikbaar stelt, tenzij
de Klant uitdrukkelijk schriftelijk bezwaar maakt binnen 30 dagen na
beschikbaarstelling. Stilzwijgende aanvaarding is bindend. Leverancier
kan de prijs aanpassen bij uitbreiding van de diensten. De Nederlandse
tekst is bindend bij tegenstrijdigheid met de Engelse versie.

[Translation: In addition to Schedule A, this Agreement includes all
services, modules, features, and expansions Provider offers during
the term, unless Client expressly objects in writing within 30 days
of availability. Silent acceptance is binding. Provider may adjust
pricing for expanded services. Dutch text governs in case of conflict.]

3. FEES
EUR 400,000 per year, subject to adjustment per Section 2.
""",
        },
    ],
}


def get_all_adversarial_contracts() -> List[Dict[str, Any]]:
    """Return all adversarial contracts for red-teaming."""
    all_contracts = []
    for category_contracts in ADVERSARIAL_CONTRACTS.values():
        all_contracts.extend(category_contracts)
    return all_contracts


async def run_red_team_evaluation(
    review_function,
    iteration: int = 1,
) -> Dict[str, Any]:
    """Run adversarial contracts through the review agent and measure failure rates."""
    adversarial_contracts = get_all_adversarial_contracts()
    results = []
    failures_by_category = {}

    logger.info(
        "Starting red-team evaluation",
        contracts=len(adversarial_contracts),
        iteration=iteration,
    )

    for contract in adversarial_contracts:
        category = contract["category"]
        hidden_risk = contract["hidden_risk"]

        try:
            review_result = await review_function(
                contract_text=contract["contract_text"],
                contract_id=contract["id"],
                contract_filename=f"{contract['id']}.pdf",
                contract_type="general",
            )

            # Check if the hidden risk was detected
            all_clauses = review_result.get("all_clauses", [])
            deal_breakers = review_result.get("deal_breakers", [])
            top_issues = review_result.get("top_5_issues", [])

            # Detection logic — check if the specific hidden risk appears in output
            detected = _check_risk_detected(hidden_risk, all_clauses, top_issues, deal_breakers)

            result = {
                "contract_id": contract["id"],
                "category": category,
                "hidden_risk": hidden_risk,
                "detected": detected,
                "expected_detection": contract["expected_detection"],
                "success": detected == contract["expected_detection"],
                "risk_level_assigned": review_result.get("overall_risk_level", "unknown"),
            }
            results.append(result)

            if category not in failures_by_category:
                failures_by_category[category] = {"total": 0, "failed": 0}
            failures_by_category[category]["total"] += 1
            if not result["success"]:
                failures_by_category[category]["failed"] += 1

        except Exception as e:
            logger.error("Red team contract failed", contract_id=contract["id"], error=str(e))
            results.append({
                "contract_id": contract["id"],
                "category": category,
                "error": str(e),
                "success": False,
            })

    # Calculate failure rates
    total = len(results)
    failed = sum(1 for r in results if not r.get("success", False))
    failure_rate = failed / total if total > 0 else 0.0

    category_failure_rates = {}
    for cat, counts in failures_by_category.items():
        category_failure_rates[cat] = {
            "failure_rate": round(counts["failed"] / counts["total"], 3) if counts["total"] > 0 else 0.0,
            "failed": counts["failed"],
            "total": counts["total"],
        }

    # Emit to Datadog
    metrics.red_team_run_completed(
        iteration=iteration,
        total_contracts=total,
        failure_rate=failure_rate,
        category_results=category_failure_rates,
    )
    return {
        "iteration": iteration,
        "total_adversarial_contracts": total,
        "total_failed": failed,
        "failure_rate": round(failure_rate, 3),
        "success_rate": round(1 - failure_rate, 3),
        "category_breakdown": category_failure_rates,
        "individual_results": results,
        "evaluated_at": datetime.utcnow().isoformat(),
    }


def _check_risk_detected(
    hidden_risk: str,
    clauses: List[Dict],
    top_issues: List[Dict],
    deal_breakers: List,
) -> bool:
    """Check if a specific hidden risk was detected in the review output."""
    risk_to_keywords = {
        "data_rights_waiver": ["data", "training", "model", "ai", "anonymized", "license", "perpetual"],
        "liability_cap_inadequate": ["liability", "cap", "limit", "formula", "calculation", "inadequate"],
        "auto_renewal": ["renewal", "renew", "evergreen", "perpetuity", "automatic"],
        "ip_ownership_risk": ["intellectual property", "ip", "ownership", "schedule b", "exception", "provider technology"],
    }

    keywords = risk_to_keywords.get(hidden_risk, [])
    if not keywords:
        return False

    # Check in clauses
    for clause in clauses:
        clause_text = (
            clause.get("clause_text", "") + " " +
            clause.get("risk_reasoning", "") + " " +
            clause.get("clause_type", "")
        ).lower()
        if any(k in clause_text for k in keywords):
            if clause.get("risk_level", "low") in ["high", "critical", "medium"]:
                return True

    # Check in top issues
    for issue in top_issues:
        issue_text = str(issue).lower()
        if any(k in issue_text for k in keywords):
            return True

    # Check in deal breakers
    deal_breaker_text = str(deal_breakers).lower()
    if any(k in deal_breaker_text for k in keywords):
        return True

    return False


def generate_patch_recommendations(
    red_team_results: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Generate prompt patches based on red-team failures."""
    failures = [r for r in red_team_results.get("individual_results", []) if not r.get("success", True)]
    patches = []

    category_failures = {}
    for failure in failures:
        cat = failure.get("category", "unknown")
        if cat not in category_failures:
            category_failures[cat] = []
        category_failures[cat].append(failure)

    for category, cat_failures in category_failures.items():
        if category == "buried_data_rights":
            patches.append({
                "category": category,
                "patch_type": "system_prompt",
                "description": "Add explicit instruction to scan for data usage permissions buried in service improvement, analytics, and operational clauses",
                "prompt_addition": "CRITICAL: Scan ALL clauses for data rights implications, especially within 'service improvement', 'analytics', 'operational data', and 'anonymized data' sections. Any grant of rights to use client data for AI/ML training is a CRITICAL risk regardless of where it appears.",
                "expected_improvement": "Fewer missed data-rights waivers embedded in operational clauses",
            })
        elif category == "disguised_liability":
            patches.append({
                "category": category,
                "patch_type": "system_prompt",
                "description": "Add instruction to compute actual liability cap values when expressed as formulas",
                "prompt_addition": "When reviewing liability caps: if expressed as a formula or calculation, COMPUTE the actual dollar value based on contract pricing information. Flag if computed cap is less than 10% of contract value as HIGH risk, less than 1% as CRITICAL.",
                "expected_improvement": "Fewer missed inadequate liability caps expressed as formulas",
            })
        elif category == "auto_renewal_disguised":
            patches.append({
                "category": category,
                "patch_type": "system_prompt",
                "description": "Add non-standard auto-renewal terminology to detection vocabulary",
                "prompt_addition": "Check for auto-renewal using ALL of these terms: 'automatically renew', 'evergreen', 'perpetuity', 'continues unless terminated', 'successive terms', 'rolling renewal'. Any of these without a clear opt-out mechanism is HIGH risk.",
                "expected_improvement": "Fewer missed auto-renewal clauses using non-standard terminology",
            })
        elif category == "cross_reference_exploit":
            patches.append({
                "category": category,
                "patch_type": "system_prompt",
                "description": "Require cross-reference resolution for all schedule and exhibit references",
                "prompt_addition": "MANDATORY: For every clause that references a Schedule, Exhibit, or Appendix, read that referenced document and assess the COMBINED effect of the main clause plus its references. A clause that appears safe in isolation but references a Schedule that negates its protections must be flagged.",
                "expected_improvement": "Fewer failures on clauses neutralised by schedule or exhibit cross-references",
            })

    return patches
