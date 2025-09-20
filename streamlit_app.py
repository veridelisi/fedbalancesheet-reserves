import streamlit as st

st.set_page_config(page_title="Veridelisi • Analytics Portal", layout="wide", page_icon="📊")

# Enhanced CSS styling
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
        
        /* Enhanced project cards */
        .project-card {
            background: white;
            border-radius: 16px;
            padding: 1.5rem;
            margin: 1rem 0;
            box-shadow: 0 8px 32px rgba(0,0,0,0.08);
            border: 1px solid #e2e8f0;
            transition: all 0.3s ease;
            height: 100%;
        }
        
        .project-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 16px 48px rgba(0,0,0,0.12);
            border-color: #667eea;
        }
        
        .card-badge {
            display: inline-block;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .card-title {
            font-size: 1.4rem;
            font-weight: 600;
            color: #1e293b;
            margin: 0.5rem 0;
            line-height: 1.3;
        }
        
        .card-tagline {
            color: #64748b;
            font-size: 0.9rem;
            font-style: italic;
            margin-bottom: 1rem;
        }
        
        .card-description {
            color: #475569;
            line-height: 1.6;
            margin-bottom: 1.5rem;
        }
        
        .card-link {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
            padding: 0.75rem 1.5rem;
            border-radius: 10px;
            text-decoration: none;
            font-weight: 600;
            display: inline-block;
            transition: all 0.3s ease;
            border: none;
        }
        
        .card-link:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(102, 126, 234, 0.3);
            color: white !important;
            text-decoration: none;
        }
        
        /* Stats section */
        .stats-container {
            background: #f8fafc;
            border-radius: 16px;
            padding: 2rem;
            margin: 2rem 0;
            text-align: center;
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
        }
        
        /* Category headers */
        .category-header {
            background: linear-gradient(90deg, #f1f5f9 0%, #e2e8f0 100%);
            padding: 1rem 1.5rem;
            border-radius: 12px;
            margin: 2rem 0 1rem 0;
            border-left: 4px solid #667eea;
        }
        
        .category-title {
            font-size: 1.3rem;
            font-weight: 600;
            color: #1e293b;
            margin: 0;
        }
        
        .category-subtitle {
            font-size: 0.9rem;
            color: #64748b;
            margin: 0.25rem 0 0 0;
        }
        
        /* Footer styling */
        .footer {
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            color: white;
            padding: 2rem;
            border-radius: 16px;
            text-align: center;
            margin-top: 3rem;
        }
        
        .footer a {
            color: #60a5fa;
            text-decoration: none;
            font-weight: 600;
        }
        
        .footer a:hover {
            color: #93c5fd;
        }
    </style>
    """, unsafe_allow_html=True)

# Hero Section
st.markdown("""
    <div class="hero-container">
        <div class="hero-title">📊 Veridelisi Analytics Portal</div>
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

# Enhanced project card function
def enhanced_project_card(title: str, tagline: str, description_md: str, page_path: str, 
                         image_path: str, link_label: str, badge_text: str = "Dashboard", 
                         badge_color: str = "#10b981"):
    
    card_html = f"""
    <div class="project-card">
        <div class="card-badge" style="background: linear-gradient(135deg, {badge_color} 0%, {badge_color}dd 100%);">
            {badge_text}
        </div>
        <h3 class="card-title">{title}</h3>
        <div class="card-tagline">{tagline}</div>
        <div class="card-description">{description_md}</div>
    </div>
    """
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(card_html, unsafe_allow_html=True)
        st.page_link(page_path, label=link_label)
    
    with col2:
        try:
            st.image(image_path, use_column_width=True)
        except:
            # Fallback if image doesn't exist
            st.markdown("""
                <div style="
                    background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
                    height: 120px;
                    border-radius: 12px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: #64748b;
                    font-size: 2rem;
                ">📊</div>
            """, unsafe_allow_html=True)

# Federal Reserve & Monetary Policy Section
st.markdown("""
    <div class="category-header">
        <h2 class="category-title">🏦 Federal Reserve & Monetary Policy</h2>
        <p class="category-subtitle">Track Fed operations, balance sheet changes, and monetary policy implementation</p>
    </div>
    """, unsafe_allow_html=True)

enhanced_project_card(
    title="Fed Assets & Liabilities Impact on Bank Reserves",
    tagline="Federal Reserve H.4.1 weekly release • Reserve drivers analysis",
    description_md=(
        "Comprehensive tracking of the Fed's weekly H.4.1 release with detailed breakdowns of "
        "assets and liabilities. Identify primary drivers of reserve fluctuations and assess "
        "their impact on overall liquidity conditions with interactive charts and smart analytics."
    ),
    page_path="pages/01_Reserves.py",
    image_path="assets/thumbs/veridelisi_reserves_thumb.jpg",
    link_label="🔍 Explore Reserves Dashboard",
    badge_text="Weekly Data",
    badge_color="#3b82f6"
)

enhanced_project_card(
    title="NY Fed Desk Operations",
    tagline="Daily & weekly market operations • Real-time monitoring",
    description_md=(
        "Monitor the Federal Reserve's daily market operations including repo and reverse repo "
        "activities. Track operational flows, market interventions, and policy implementation "
        "tools with historical context and trend analysis."
    ),
    page_path="pages/01_Desk.py",
    image_path="assets/thumbs/desk1.jpeg",
    link_label="🔍 View Desk Operations",
    badge_text="Daily Ops",
    badge_color="#8b5cf6"
)

# Money Markets Section
st.markdown("""
    <div class="category-header">
        <h2 class="category-title">💰 Money Markets & Reference Rates</h2>
        <p class="category-subtitle">Monitor short-term funding markets and benchmark rates</p>
    </div>
    """, unsafe_allow_html=True)

enhanced_project_card(
    title="Primary Dealer Repo & Reverse Repo",
    tagline="NY Fed Primary Dealer Statistics • Net position analysis",
    description_md=(
        "Comprehensive view of primary dealer repo activities across all segments: uncleared/cleared "
        "bilateral, GCF, and tri-party. Analyze net market positions and understand dealer roles "
        "in short-term funding dynamics with advanced visualizations."
    ),
    page_path="pages/01_Repo.py",
    image_path="assets/thumbs/dealer.png",
    link_label="🔍 Analyze Repo Markets",
    badge_text="Market Data",
    badge_color="#f59e0b"
)

enhanced_project_card(
    title="Money Market Reference Rates",
    tagline="EFFR, OBFR, SOFR, BGCR, TGCR • NY Fed reference rates",
    description_md=(
        "Track the latest levels and historical trends of key money market rates. Features "
        "7-day and YTD views with user-selectable series and SOFR-centered design for "
        "clean rate comparisons and spread analysis."
    ),
    page_path="pages/01_Interest.py",
    image_path="assets/thumbs/interest.png",
    link_label="🔍 Monitor Interest Rates",
    badge_text="Live Rates",
    badge_color="#ef4444"
)

enhanced_project_card(
    title="Eurodollar Market Evolution",
    tagline="BIS Global Liquidity Indicators • USD credit analysis",
    description_md=(
        "Track the evolution of the global Eurodollar market from 2000 to present. Analyze "
        "total credit, debt securities, and loans with YoY views, crisis period shading, "
        "and Fed policy cycle context for comprehensive market understanding."
    ),
    page_path="pages/01_Eurodollar.py",
    image_path="assets/thumbs/bis.png",
    link_label="🔍 Explore Eurodollar Market",
    badge_text="Global Data",
    badge_color="#06b6d4"
)

# Treasury & Fiscal Section
st.markdown("""
    <div class="category-header">
        <h2 class="category-title">🏛️ Treasury Operations & Fiscal Analytics</h2>
        <p class="category-subtitle">Daily Treasury operations, cash flows, and fiscal position monitoring</p>
    </div>
    """, unsafe_allow_html=True)

enhanced_project_card(
    title="Treasury General Account (TGA) Cash Position",
    tagline="Daily Treasury Statement • Operating cash balance tracking",
    description_md=(
        "Monitor daily changes in the Treasury General Account with detailed cash position "
        "statements. Features annual trend analysis, liquidity impact assessments, and "
        "historical context for understanding Treasury operations."
    ),
    page_path="pages/01_TGA.py",
    image_path="assets/thumbs/tga.png",
    link_label="🔍 Track TGA Position",
    badge_text="Daily Updates",
    badge_color="#10b981"
)

enhanced_project_card(
    title="Public Balance & Cash Flows",
    tagline="Daily Treasury Statement • Receipts, expenditures & debt operations",
    description_md=(
        "Comprehensive decomposition of daily Treasury inflows and outflows including tax "
        "receipts, expenditures, new issuance, and redemptions. Monitor top-10 categories "
        "in receipts and expenditures with trend analysis and seasonal adjustments."
    ),
    page_path="pages/01_PublicBalance.py",
    image_path="assets/thumbs/public_balance.png",
    link_label="🔍 Analyze Public Balance",
    badge_text="Cash Flows",
    badge_color="#f97316"
)

# Enhanced Footer
st.markdown("""
    <div class="footer">
        <h3 style="margin-top: 0;">About Veridelisi Analytics</h3>
        <p style="margin-bottom: 1.5rem;">
            Professional-grade financial market analytics and Federal Reserve operations monitoring. 
            Built for traders, analysts, and policymakers who need deep insights into monetary policy implementation.
        </p>
        <div style="border-top: 1px solid #475569; padding-top: 1.5rem; margin-top: 1.5rem;">
            <a href="https://veridelisi.substack.com/">📰 Veri Delisi Substack</a> • 
            <span style="color: #94a3b8;">Created by</span> 
            <strong>Engin Yılmaz</strong> • 
            <span style="color: #94a3b8;">Amherst • September 2025</span>
        </div>
    </div>
    """, unsafe_allow_html=True)