import streamlit as st

st.set_page_config(page_title="Veridelisi • Analytics Portal", layout="wide", page_icon="VD")

# Enhanced CSS styling with gradient + icon system
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none;}
        section[data-testid="stSidebar"][aria-expanded="true"]{display: none;}
        
        /* Hero section styling */
            
            
        .hero-container {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 3rem 2rem;
            border-radius: 20px;
            color: white;
            text-align: center;
            margin: 2rem 0;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        
        .hero-title {
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 1rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .hero-subtitle {
            font-size: 1.3rem;
            opacity: 0.9;
            margin-bottom: 1.5rem;
            font-weight: 300;
        }
        
        .hero-description {
            font-size: 1.1rem;
            opacity: 0.8;
            max-width: 600px;
            margin: 0 auto;
            line-height: 1.6;
        }
        
        /* Enhanced project cards with gradient + icon */
        .project-card {
            background: white;
            border-radius: 20px;
            padding: 0;
            margin: 1.5rem 0;
            box-shadow: 0 12px 40px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
            transition: all 0.4s ease;
            overflow: hidden;
            position: relative;
        }
        
        .project-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 24px 60px rgba(0,0,0,0.15);
            border-color: transparent;
        }
        
        .card-header {
            padding: 2rem 2rem 1rem 2rem;
            border-radius: 20px 20px 0 0;
            position: relative;
            color: white;
            overflow: hidden;
        }
        
        .card-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
        }
        
        .card-content {
            position: relative;
            z-index: 2;
        }
        
        .card-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
            display: block;
            filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.3));
        }
        
        .card-badge {
            display: inline-block;
            background: rgba(255,255,255,0.2);
            color: white;
            padding: 6px 16px;
            border-radius: 25px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-bottom: 1rem;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            border: 1px solid rgba(255,255,255,0.3);
        }
        
        .card-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: white;
            margin: 0;
            line-height: 1.3;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }
        
        .card-body {
            padding: 1.5rem 2rem 2rem 2rem;
        }
        
        .card-tagline {
            color: #64748b;
            font-size: 0.9rem;
            font-weight: 500;
            margin-bottom: 1rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .card-description {
            color: #475569;
            line-height: 1.7;
            margin-bottom: 1.5rem;
            font-size: 0.95rem;
        }
        
        .card-link {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
            padding: 12px 24px;
            border-radius: 12px;
            text-decoration: none;
            font-weight: 600;
            display: inline-block;
            transition: all 0.3s ease;
            border: none;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .card-link:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
            color: white !important;
            text-decoration: none;
        }
        
        /* Gradient backgrounds for each dashboard */
        .gradient-reserves { background: linear-gradient(135deg, #3b82f6 0%, #1e40af 100%); }
        .gradient-repo { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
        .gradient-tga { background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
        .gradient-balance { background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); }
        .gradient-rates { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); }
        .gradient-desk { background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); }
        .gradient-eurodollar { background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%); }
        
        /* Stats section */
        .stats-container {
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            border-radius: 20px;
            padding: 2.5rem;
            margin: 2rem 0;
            text-align: center;
            border: 1px solid #e2e8f0;
        }
        
        .stat-item {
            padding: 1rem;
        }
        
        .stat-number {
            font-size: 2.5rem;
            font-weight: 700;
            color: #667eea;
            display: block;
        }
        
        .stat-label {
            font-size: 0.9rem;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }
        
        /* Category headers */
        .category-header {
            background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
            padding: 1.5rem 2rem;
            border-radius: 16px;
            margin: 3rem 0 2rem 0;
            border-left: 5px solid #667eea;
            box-shadow: 0 4px 16px rgba(0,0,0,0.05);
        }
        
        .category-title {
            font-size: 1.4rem;
            font-weight: 700;
            color: #1e293b;
            margin: 0;
        }
        
        .category-subtitle {
            font-size: 1rem;
            color: #64748b;
            margin: 0.5rem 0 0 0;
            font-weight: 400;
        }
        
        /* Footer styling */
        .footer {
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            color: white;
            padding: 3rem 2rem;
            border-radius: 20px;
            text-align: center;
            margin-top: 4rem;
            box-shadow: 0 12px 40px rgba(0,0,0,0.1);
        }
        
        .footer a {
            color: #60a5fa;
            text-decoration: none;
            font-weight: 600;
        }
        
        .footer a:hover {
            color: #93c5fd;
        }
        
        /* Responsive design */
        @media (max-width: 768px) {
            .hero-title { font-size: 2rem; }
            .hero-subtitle { font-size: 1.1rem; }
            .card-title { font-size: 1.3rem; }
            .stats-container { padding: 1.5rem; }
        }
    </style>
    """, unsafe_allow_html=True)

# Hero Section
st.markdown("""
    <div class="hero-container">
        <div class="hero-title">💥 Veridelisi Analytics Portal</div>
        <div class="hero-subtitle">Financial Markets Intelligence & Data Analytics</div>
        <div class="hero-description">
            Comprehensive dashboards for Federal Reserve operations, money markets, and Treasury analytics. 
            Real-time insights into liquidity conditions, market structure, and monetary policy implementation.
        </div>
    </div>
    """, unsafe_allow_html=True)

# Quick Stats
st.markdown("""
    <div class="stats-container">
        <div style="display: flex; justify-content: space-around; flex-wrap: wrap;">
            <div class="stat-item">
                <span class="stat-number">7</span>
                <span class="stat-label">Dashboards</span>
            </div>
            <div class="stat-item">
                <span class="stat-number">15+</span>
                <span class="stat-label">Data Sources</span>
            </div>
            <div class="stat-item">
                <span class="stat-number">Daily</span>
                <span class="stat-label">Updates</span>
            </div>
            <div class="stat-item">
                <span class="stat-number">Real-time</span>
                <span class="stat-label">Analysis</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Enhanced project card function with gradient + icon
def gradient_project_card(title: str, tagline: str, description: str, page_path: str, 
                         link_label: str, icon: str, gradient_class: str, badge_text: str):
    
    card_html = f"""
    <div class="project-card">
        <div class="card-header {gradient_class}">
            <div class="card-content">
                <span class="card-icon">{icon}</span>
                <span class="card-badge">{badge_text}</span>
                <h3 class="card-title">{title}</h3>
            </div>
        </div>
        <div class="card-body">
            <div class="card-tagline">{tagline}</div>
            <div class="card-description">{description}</div>
        </div>
    </div>
    """
    
    st.markdown(card_html, unsafe_allow_html=True)
    st.page_link(page_path, label=link_label)

# Federal Reserve & Monetary Policy Section
st.markdown("""
    <div class="category-header">
        <h2 class="category-title">🏦 Federal Reserve & Monetary Policy</h2>
        <p class="category-subtitle">Track Fed operations, balance sheet changes, and monetary policy implementation</p>
    </div>
    """, unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")

with col1:
    gradient_project_card(
        title="Fed Assets & Liabilities Impact on Bank Reserves",
        tagline="Federal Reserve H.4.1 weekly release • Reserve drivers analysis",
        description=(
            "Comprehensive tracking of the Fed's weekly H.4.1 release with detailed breakdowns of "
            "assets and liabilities. Identify primary drivers of reserve fluctuations and assess "
            "their impact on overall liquidity conditions with interactive charts."
        ),
        page_path="pages/01_Reserves.py",
        link_label="🔍 Explore Reserves Dashboard",
        icon="🏦",
        gradient_class="gradient-reserves",
        badge_text="Weekly Data"
    )

with col2:
    gradient_project_card(
        title="NY Fed Desk Operations",
        tagline="Daily & weekly market operations • Real-time monitoring",
        description=(
            "Monitor the Federal Reserve's daily market operations including repo and reverse repo "
            "activities. Track operational flows, market interventions, and policy implementation "
            "tools with historical context and trend analysis."
        ),
        page_path="pages/01_Desk.py",
        link_label="🔍 View Desk Operations",
        icon="⚙️",
        gradient_class="gradient-desk",
        badge_text="Daily Ops"
    )

# Money Markets Section
st.markdown("""
    <div class="category-header">
        <h2 class="category-title">💰 Money Markets & Reference Rates</h2>
        <p class="category-subtitle">Monitor short-term funding markets and benchmark rates</p>
    </div>
    """, unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")

with col1:
    gradient_project_card(
        title="Primary Dealer Repo & Reverse Repo",
        tagline="NY Fed Primary Dealer Statistics • Net position analysis",
        description=(
            "Comprehensive view of primary dealer repo activities across all segments: uncleared/cleared "
            "bilateral, GCF, and tri-party. Analyze net market positions and understand dealer roles "
            "in short-term funding dynamics."
        ),
        page_path="pages/01_Repo.py",
        link_label="🔍 Analyze Repo Markets",
        icon="🔄",
        gradient_class="gradient-repo",
        badge_text="Market Data"
    )

with col2:
    gradient_project_card(
        title="Money Market Reference Rates",
        tagline="EFFR, OBFR, SOFR, BGCR, TGCR • NY Fed reference rates",
        description=(
            "Track the latest levels and historical trends of key money market rates. Features "
            "7-day and YTD views with user-selectable series and SOFR-centered design for "
            "clean rate comparisons and spread analysis."
        ),
        page_path="pages/01_Interest.py",
        link_label="🔍 Monitor Interest Rates",
        icon="📈",
        gradient_class="gradient-rates",
        badge_text="Live Rates"
    )

col1, col2 = st.columns(2, gap="large")

with col1:
    gradient_project_card(
        title="Eurodollar Market Evolution",
        tagline="BIS Global Liquidity Indicators • USD credit analysis",
        description=(
            "Track the evolution of the global Eurodollar market from 2000 to present. Analyze "
            "total credit, debt securities, and loans with YoY views, crisis period shading, "
            "and Fed policy cycle context for comprehensive market understanding."
        ),
        page_path="pages/01_Eurodollar.py",
        link_label="🔍 Explore Eurodollar Market",
        icon="🌍",
        gradient_class="gradient-eurodollar",
        badge_text="Global Data"
    )

with col2:
    st.write("")  # Empty column for balance

# Treasury & Fiscal Section
st.markdown("""
    <div class="category-header">
        <h2 class="category-title">🏛️ Treasury Operations & Fiscal Analytics</h2>
        <p class="category-subtitle">Daily Treasury operations, cash flows, and fiscal position monitoring</p>
    </div>
    """, unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")

with col1:
    gradient_project_card(
        title="Treasury General Account (TGA) Cash Position",
        tagline="Daily Treasury Statement • Operating cash balance tracking",
        description=(
            "Monitor daily changes in the Treasury General Account with detailed cash position "
            "statements. Features annual trend analysis, liquidity impact assessments, and "
            "historical context for understanding Treasury operations."
        ),
        page_path="pages/01_TGA.py",
        link_label="🔍 Track TGA Position",
        icon="🏛️",
        gradient_class="gradient-tga",
        badge_text="Daily Updates"
    )

with col2:
    gradient_project_card(
        title="Public Balance & Cash Flows",
        tagline="Daily Treasury Statement • Receipts, expenditures & debt operations",
        description=(
            "Comprehensive decomposition of daily Treasury inflows and outflows including tax "
            "receipts, expenditures, new issuance, and redemptions. Monitor top-10 categories "
            "in receipts and expenditures with trend analysis and seasonal adjustments."
        ),
        page_path="pages/01_PublicBalance.py",
        link_label="🔍 Analyze Public Balance",
        icon="📊",
        gradient_class="gradient-balance",
        badge_text="Cash Flows"
    )

# Enhanced Footer
st.markdown("""
    <div class="footer">
        <h3 style="margin-top: 0;">About Veridelisi Analytics</h3>
        <p style="margin-bottom: 1.5rem;">
            Professional-grade financial market analytics and Federal Reserve operations monitoring. 
            Built for researchers, analysts, and policymakers who need deep insights into monetary policy implementation.
        </p>
        <div style="border-top: 1px solid #475569; padding-top: 1.5rem; margin-top: 1.5rem;">
    <a href="https://veridelisi.substack.com/">📰 Veri Delisi Substack</a><br>
    <span style="color: #94a3b8;">Created by</span> 
    <strong>Engin Yılmaz</strong> • 
    <span style="color: #94a3b8;">Amherst • September 2025</span>
</div>
    </div>
    """, unsafe_allow_html=True)