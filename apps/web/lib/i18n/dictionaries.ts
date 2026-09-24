export const languages = ["es", "en"] as const;

export type Language = (typeof languages)[number];

type TranslationTree = {
  [key: string]: string | TranslationTree;
};

export const defaultLanguage: Language = "es";

export const dictionaries: Record<Language, TranslationTree> = {
  es: {
    common: {
      language: "Idioma",
      spanish: "ES",
      english: "EN",
      loading: "Cargando",
      upgrade: "Upgrade",
      premium: "Premium",
      free: "Free",
      dashboard: "Dashboard",
      profile: "Mi perfil",
      jobs: "Jobs",
      ats: "ATS",
      realityGap: "Reality Gap",
      interviewKits: "Interview Kits",
      admin: "Administración",
      startFree: "Empezar gratis",
      login: "Iniciar sesión",
      register: "Registrarse",
      close: "Cerrar",
      openMenu: "Abrir menú",
      closeMenu: "Cerrar navegación",
      coldStartTitle: "Seguimos trabajando en tu pedido",
      coldStartBody:
        "Esto tarda más de lo normal. Si el servidor estaba inactivo, puede demorar hasta un minuto en arrancar."
    },
    landing: {
      navFeatures: "Funciones",
      navHow: "Cómo funciona",
      navPricing: "Precios",
      navDemo: "Vista previa",
      heroTitle:
        "Dejá de postularte a ciegas. Descubrí tu match laboral perfecto.",
      heroSubtitle:
        "Nuestra IA analiza tu CV frente a cualquier oferta de empleo para darte una puntuación de compatibilidad exacta e identificar brechas clave instantáneamente.",
      heroCta: "Analizá tu primer puesto gratis",
      problemTitle: "Postulás a 50 puestos. Te responden 3.",
      problemSubtitle:
        "La mayoría de los rechazos no son por falta de skills: son por gaps invisibles, cómo lee tu CV el ATS, si tu seniority matchea, o si tu perfil está bien representado.",
      features: {
        matchTitle: "Match Score",
        matchDescription:
          "Compatibilidad numérica 0-100 entre tu perfil y el puesto.",
        atsTitle: "ATS Analyzer",
        atsDescription:
          "Verificá si tu CV pasa filtros automáticos de reclutamiento.",
        gapTitle: "Reality Gap",
        gapDescription: "Detectá incoherencias entre tu CV, LinkedIn y perfil real.",
        optimizerTitle: "CV Optimizer",
        optimizerDescription: "Reescribí tu CV con IA para el puesto específico.",
        kitTitle: "Interview Kit",
        kitDescription: "Kit completo para preparación previa a la entrevista."
      },
      howTitle: "Cómo funciona",
      steps: {
        oneTitle: "Analizá tu CV",
        oneDescription:
          "Pegá una URL, subí el puesto y elegí contra qué rol competir.",
        twoTitle: "Descubrí gaps",
        twoDescription:
          "Verificá si tu CV pasa ATS y dónde faltan señales concretas.",
        threeTitle: "Analizá un puesto",
        threeDescription: "Conectá tu perfil con recomendaciones accionables."
      },
      demoEyebrow: "Demo visual",
      demoTitle: "Mirá cómo se ve tu análisis",
      demoSubtitle:
        "Una vista de muestra para entender qué recibe tu perfil después de analizar un puesto.",
      sampleData: "Datos de muestra",
      semantic: "semántico",
      literal: "literal",
      missing: "ausente",
      atsHint:
        "El CV cubre bien el stack principal, pero falta reforzar infraestructura.",
      kitStrength: "Fortaleza",
      kitStrengthBody: "Experiencia clara en APIs y producto.",
      kitRisk: "Riesgo",
      kitRiskBody: "Preparar una historia concreta sobre escala.",
      kitQuestion: "Pregunta",
      kitQuestionBody: "¿Cómo mide el equipo el impacto técnico?",
      kitPlan: "Plan",
      kitPlanBody: "Repasar logros con métricas antes de la entrevista.",
      demoFootnote: "Datos de muestra, sin conexión al backend.",
      pricingEyebrow: "Precios",
      pricingTitle: "Empezá gratis. Mejorá cuando lo necesites.",
      monthly: "Mensual",
      yearly: "Anual",
      perMonth: "mes",
      perYear: "año",
      freeDescription: "Para validar tu primer análisis.",
      premiumDescription: "Para preparar cada postulación con más contexto.",
      mostPopular: "Más popular",
      freeFeatures: {
        one: "10 análisis de puestos por mes",
        two: "Match Score completo",
        three: "ATS Analyzer básico",
        four: "Historial de últimos 10 puestos"
      },
      premiumFeatures: {
        one: "Análisis ilimitados",
        two: "CV Optimizer con IA",
        three: "Interview Kit premium",
        four: "Historial completo",
        five: "Recomendaciones priorizadas"
      },
      finalCta: "Empezá a prepararte mejor",
      footerDescription:
        "IA para entender mejor cada postulación antes de aplicar.",
      privacy: "Privacidad",
      terms: "Términos"
    },
    auth: {
      layoutSubtitle:
        "Ordená tu perfil, entendé tus gaps y llegá mejor preparado a cada postulación.",
      bulletMatch: "Match score real basado en tu CV",
      bulletKit: "Kit de entrevista personalizado",
      bulletFree: "Empezá gratis, sin tarjeta",
      loginHeadline: "Tu próxima entrevista empieza acá",
      loginEyebrow: "Bienvenido de vuelta",
      loginTitle: "Iniciar sesión",
      loginSubtitle:
        "Entrá para analizar puestos, revisar matches y preparar tus próximas entrevistas.",
      email: "Email",
      password: "Contraseña",
      showPassword: "Mostrar contraseña",
      hidePassword: "Ocultar contraseña",
      capsLockOn: "Bloq Mayús está activado",
      signOut: "Cerrar sesión",
      signingOut: "Cerrando sesión...",
      signedOut: "Cerraste sesión. Para volver a entrar, iniciá sesión.",
      signOutFailed: "No pudimos cerrar la sesión. Revisá tu conexión y probá de nuevo.",
      forgotPassword: "¿Olvidaste tu contraseña?",
      passwordReset:
        "Tu contraseña se actualizó correctamente. Iniciá sesión.",
      loggingIn: "Ingresando...",
      googleOpening: "Abriendo Google...",
      googleContinue: "Continuar con Google",
      noAccount: "¿No tenés cuenta?",
      hasAccount: "¿Ya tenés cuenta?",
      protectedBy: "Usamos Supabase Auth para proteger tu sesión.",
      registerHeadline: "Empezá a prepararte mejor",
      registerEyebrow: "Cuenta nueva",
      registerTitle: "Registrarse",
      registerSubtitle:
        "Creá tu cuenta y empezá desde el dashboard. Después podés completar tu perfil paso a paso.",
      fullName: "Nombre completo",
      minPassword: "Mínimo 6 caracteres",
      tos:
        "Acepto los Términos de Servicio y el procesamiento de mis datos con sistemas de IA para generar análisis del servicio.",
      tosRequired: "Tenés que aceptar los Términos de Servicio para registrarte.",
      creating: "Creando cuenta...",
      authError: "No pudimos completar la autenticación. Probá de nuevo.",
      registerError: "No pudimos completar el registro. Probá de nuevo."
    },
    app: {
      activeSession: "Sesión activa",
      careerIntelligence: "Career intelligence",
      upgradeText: "Desbloqueá kits de entrevista y optimización de CV.",
      goodMorning: "Buenos días",
      goodAfternoon: "Buenas tardes",
      goodNight: "Buenas noches",
      loadingSummary: "Cargando resumen",
      summaryError: "No se pudo cargar el resumen.",
      profileReady: "Tu perfil está listo para análisis precisos.",
      profileAt: "Tu perfil está al {percent}%. {tip}",
      profileFallback:
        "Tu perfil está al {percent}% y en estado {label}. Completá los datos pendientes para mejorar la precisión.",
      completeness: "Completeness del perfil",
      goal: "Meta: 100%",
      completeProfile: "Completar perfil",
      globalScore: "Score global",
      analysisHero: "Hero de análisis",
      analyzeNewJob: "Analizá un nuevo puesto",
      analyzeDescription:
        "Pegá una URL o el texto completo del aviso para iniciar el análisis.",
      suggestionsTitle: "Sugerencias de Jobby",
      suggestionsSubtitle:
        "Usamos tu perfil actual para anticipar qué mirar antes de aplicar.",
      suggestionsFooter:
        "Al analizar un puesto, estas alertas se vuelven específicas para ese rol y priorizan skills, ATS y brechas reales.",
      latestMatches: "Últimos 5 matches",
      latestMatchesDescription:
        "Tus análisis recientes aparecen ordenados por actividad.",
      unnamedCompany: "Empresa sin nombre",
      untitledRole: "Rol sin título",
      viewReport: "Ver reporte",
      noMatches: "Todavía no hay matches",
      noMatchesDescription:
        "Analizá tu primer puesto para ver empresa, rol, score y reporte.",
      jobUrl: "URL del puesto",
      pasteText: "Pegar texto",
      scrapingWarning:
        "Algunos sitios bloquean scraping automático. Si falla, vas a poder pegar el texto manualmente.",
      pasteJobDescription: "Pegá acá la descripción completa del puesto",
      enqueueing: "Encolando...",
      analyzeJob: "Analizar job",
      analysisComplete: "Análisis completo. Ya podés revisar el job.",
      urlReadFail:
        "No pudimos leer esa URL. Pegá el texto del puesto para continuar.",
      analysisQueued: "Analizando... te avisamos cuando esté listo.",
      analysisStartFail: "No se pudo iniciar el análisis."
    },
    admin: {
      title: "Administración",
      subtitle:
        "Métricas agregadas de Jobby. Nunca incluyen el CV ni los datos personales de nadie.",
      updated: "Actualizado: {time}",
      loading: "Cargando métricas",
      forbidden: "No tenés permisos para ver esta sección.",
      error: "No se pudieron cargar las métricas.",
      backToDashboard: "Volver al dashboard",
      people: "Personas",
      plans: "{free} free · {premium} premium",
      newThisWeek: "+{count} en los últimos 7 días",
      cvs: "CV subidos",
      cvsDone: "{count} procesados",
      failed: "{count} con error",
      inProgress: "{count} en curso",
      jobs: "Puestos analizados",
      matches: "Matches",
      averageScore: "Score promedio: {score}",
      noScore: "Todavía sin score promedio",
      averageRating: "Valoración: {rating}/5 ({count} votos)",
      noRatings: "Todavía sin valoraciones",
      kits: "Kits de entrevista",
      kitsDone: "{count} generados",
      activity: "Actividad de los últimos 14 días",
      activityNote:
        "Una barra por día, en horario UTC. Pasá el cursor o el foco por una barra para ver su valor.",
      cvsPerDay: "CV subidos por día",
      jobsPerDay: "Puestos analizados por día",
      matchesPerDay: "Matches por día",
      unitCvs: "CV",
      unitJobs: "puestos",
      unitMatches: "matches",
      showTable: "Ver los datos en una tabla",
      day: "Día"
    },
    pricing: {
      title: "Elegí tu plan",
      subtitle:
        "Empezá gratis y pasá a Premium cuando quieras preparar entrevistas, analizar más puestos y desbloquear IA avanzada.",
      freeDescription: "Para validar tu primer flujo.",
      premiumDescription:
        "Para aplicar con reportes completos y preparación personalizada.",
      followFree: "Seguir gratis",
      redirecting: "Redirigiendo al checkout...",
      checkoutFail: "No se pudo iniciar el checkout.",
      successTitle: "¡Listo! Tu cuenta ya es Premium",
      successBody:
        "El estado final se refleja cuando Lemon Squeezy confirma el pago por webhook y el dashboard vuelve a cargar tus datos.",
      goDashboard: "Ir al dashboard",
      publicSuccessTitle: "Pago confirmado",
      publicSuccessBody:
        "Tu plan Premium se activará cuando Lemon Squeezy confirme la suscripción por webhook. Esto suele tardar unos segundos."
    }
  },
  en: {
    common: {
      language: "Language",
      spanish: "ES",
      english: "EN",
      loading: "Loading",
      upgrade: "Upgrade",
      premium: "Premium",
      free: "Free",
      dashboard: "Dashboard",
      profile: "My profile",
      jobs: "Jobs",
      ats: "ATS",
      realityGap: "Reality Gap",
      interviewKits: "Interview Kits",
      admin: "Admin",
      startFree: "Start free",
      login: "Log in",
      register: "Sign up",
      close: "Close",
      openMenu: "Open menu",
      closeMenu: "Close navigation",
      coldStartTitle: "We are still working on your request",
      coldStartBody:
        "This is taking longer than usual. If the server was idle, it can take up to a minute to start."
    },
    landing: {
      navFeatures: "Features",
      navHow: "How it works",
      navPricing: "Pricing",
      navDemo: "Preview",
      heroTitle: "Stop applying blind. Find your perfect job match.",
      heroSubtitle:
        "Our AI compares your CV with any job post, gives you an exact compatibility score, and spots key gaps instantly.",
      heroCta: "Analyze your first job for free",
      problemTitle: "You apply to 50 jobs. 3 reply.",
      problemSubtitle:
        "Most rejections are not about missing skills: they come from invisible gaps, how ATS reads your CV, whether your seniority matches, or whether your profile is represented clearly.",
      features: {
        matchTitle: "Match Score",
        matchDescription:
          "A 0-100 compatibility score between your profile and the job.",
        atsTitle: "ATS Analyzer",
        atsDescription: "Check whether your CV passes automated recruiting filters.",
        gapTitle: "Reality Gap",
        gapDescription:
          "Spot inconsistencies between your CV, LinkedIn, and real profile.",
        optimizerTitle: "CV Optimizer",
        optimizerDescription: "Rewrite your CV with AI for a specific job.",
        kitTitle: "Interview Kit",
        kitDescription: "A complete kit to prepare before the interview."
      },
      howTitle: "How it works",
      steps: {
        oneTitle: "Analyze your CV",
        oneDescription: "Paste a URL, add the job, and choose the role to compare.",
        twoTitle: "Discover gaps",
        twoDescription:
          "Check if your CV passes ATS and where concrete signals are missing.",
        threeTitle: "Analyze a job",
        threeDescription: "Connect your profile with actionable recommendations."
      },
      demoEyebrow: "Visual demo",
      demoTitle: "See what your analysis looks like",
      demoSubtitle:
        "A sample view of what your profile receives after analyzing a job.",
      sampleData: "Sample data",
      semantic: "semantic",
      literal: "literal",
      missing: "missing",
      atsHint:
        "The CV covers the main stack well, but infrastructure needs more evidence.",
      kitStrength: "Strength",
      kitStrengthBody: "Clear experience in APIs and product work.",
      kitRisk: "Risk",
      kitRiskBody: "Prepare a concrete story about scale.",
      kitQuestion: "Question",
      kitQuestionBody: "How does the team measure technical impact?",
      kitPlan: "Plan",
      kitPlanBody: "Review achievements with metrics before the interview.",
      demoFootnote: "Sample data, no backend connection.",
      pricingEyebrow: "Pricing",
      pricingTitle: "Start free. Upgrade when you need more.",
      monthly: "Monthly",
      yearly: "Yearly",
      perMonth: "month",
      perYear: "year",
      freeDescription: "To validate your first analysis.",
      premiumDescription: "To prepare each application with more context.",
      mostPopular: "Most popular",
      freeFeatures: {
        one: "10 job analyses per month",
        two: "Complete Match Score",
        three: "Basic ATS Analyzer",
        four: "Last 10 jobs history"
      },
      premiumFeatures: {
        one: "Unlimited analyses",
        two: "AI CV Optimizer",
        three: "Premium Interview Kit",
        four: "Full history",
        five: "Prioritized recommendations"
      },
      finalCta: "Start preparing better",
      footerDescription: "AI to understand every application before you apply.",
      privacy: "Privacy",
      terms: "Terms"
    },
    auth: {
      layoutSubtitle:
        "Organize your profile, understand your gaps, and arrive better prepared to every application.",
      bulletMatch: "Real match score based on your CV",
      bulletKit: "Personalized interview kit",
      bulletFree: "Start free, no card required",
      loginHeadline: "Your next interview starts here",
      loginEyebrow: "Welcome back",
      loginTitle: "Log in",
      loginSubtitle:
        "Log in to analyze jobs, review matches, and prepare your next interviews.",
      email: "Email",
      password: "Password",
      showPassword: "Show password",
      hidePassword: "Hide password",
      capsLockOn: "Caps Lock is on",
      signOut: "Sign out",
      signingOut: "Signing out...",
      signedOut: "You signed out. Log in to come back.",
      signOutFailed: "We could not sign you out. Check your connection and try again.",
      forgotPassword: "Forgot your password?",
      passwordReset: "Your password was updated. Log in again.",
      loggingIn: "Logging in...",
      googleOpening: "Opening Google...",
      googleContinue: "Continue with Google",
      noAccount: "No account yet?",
      hasAccount: "Already have an account?",
      protectedBy: "We use Supabase Auth to protect your session.",
      registerHeadline: "Start preparing better",
      registerEyebrow: "New account",
      registerTitle: "Sign up",
      registerSubtitle:
        "Create your account and start from the dashboard. You can complete your profile step by step later.",
      fullName: "Full name",
      minPassword: "At least 6 characters",
      tos:
        "I accept the Terms of Service and the processing of my data with AI systems to generate service analyses.",
      tosRequired: "You need to accept the Terms of Service to sign up.",
      creating: "Creating account...",
      authError: "We could not complete authentication. Try again.",
      registerError: "We could not complete signup. Try again."
    },
    app: {
      activeSession: "Active session",
      careerIntelligence: "Career intelligence",
      upgradeText: "Unlock interview kits and CV optimization.",
      goodMorning: "Good morning",
      goodAfternoon: "Good afternoon",
      goodNight: "Good evening",
      loadingSummary: "Loading summary",
      summaryError: "Could not load the summary.",
      profileReady: "Your profile is ready for precise analyses.",
      profileAt: "Your profile is at {percent}%. {tip}",
      profileFallback:
        "Your profile is at {percent}% and in {label} state. Complete pending data to improve precision.",
      completeness: "Profile completeness",
      goal: "Goal: 100%",
      completeProfile: "Complete profile",
      globalScore: "Global score",
      analysisHero: "Analysis hero",
      analyzeNewJob: "Analyze a new job",
      analyzeDescription:
        "Paste a URL or the full job description to start the analysis.",
      suggestionsTitle: "Jobby suggestions",
      suggestionsSubtitle:
        "We use your current profile to anticipate what to check before applying.",
      suggestionsFooter:
        "When you analyze a job, these alerts become specific to that role and prioritize skills, ATS, and real gaps.",
      latestMatches: "Latest 5 matches",
      latestMatchesDescription: "Your recent analyses appear sorted by activity.",
      unnamedCompany: "Unnamed company",
      untitledRole: "Untitled role",
      viewReport: "View report",
      noMatches: "No matches yet",
      noMatchesDescription:
        "Analyze your first job to see company, role, score, and report.",
      jobUrl: "Job URL",
      pasteText: "Paste text",
      scrapingWarning:
        "Some sites block automatic scraping. If it fails, you can paste the text manually.",
      pasteJobDescription: "Paste the full job description here",
      enqueueing: "Queueing...",
      analyzeJob: "Analyze job",
      analysisComplete: "Analysis complete. You can review the job now.",
      urlReadFail: "We could not read that URL. Paste the job text to continue.",
      analysisQueued: "Analyzing... we will let you know when it is ready.",
      analysisStartFail: "Could not start the analysis."
    },
    admin: {
      title: "Administration",
      subtitle: "Aggregated Jobby metrics. They never include anyone's CV or personal data.",
      updated: "Updated: {time}",
      loading: "Loading metrics",
      forbidden: "You do not have permission to see this section.",
      error: "Could not load the metrics.",
      backToDashboard: "Back to dashboard",
      people: "People",
      plans: "{free} free · {premium} premium",
      newThisWeek: "+{count} in the last 7 days",
      cvs: "Uploaded CVs",
      cvsDone: "{count} processed",
      failed: "{count} failed",
      inProgress: "{count} in progress",
      jobs: "Analyzed jobs",
      matches: "Matches",
      averageScore: "Average score: {score}",
      noScore: "No average score yet",
      averageRating: "Rating: {rating}/5 ({count} votes)",
      noRatings: "No ratings yet",
      kits: "Interview kits",
      kitsDone: "{count} generated",
      activity: "Activity in the last 14 days",
      activityNote: "One bar per day, in UTC. Hover or focus a bar to see its value.",
      cvsPerDay: "CVs uploaded per day",
      jobsPerDay: "Jobs analyzed per day",
      matchesPerDay: "Matches per day",
      unitCvs: "CVs",
      unitJobs: "jobs",
      unitMatches: "matches",
      showTable: "Show the data as a table",
      day: "Day"
    },
    pricing: {
      title: "Choose your plan",
      subtitle:
        "Start free and move to Premium when you want to prepare interviews, analyze more jobs, and unlock advanced AI.",
      freeDescription: "To validate your first flow.",
      premiumDescription:
        "To apply with complete reports and personalized preparation.",
      followFree: "Stay free",
      redirecting: "Redirecting to checkout...",
      checkoutFail: "Could not start checkout.",
      successTitle: "Done! Your account is now Premium",
      successBody:
        "The final status updates when Lemon Squeezy confirms payment by webhook and the dashboard reloads your data.",
      goDashboard: "Go to dashboard",
      publicSuccessTitle: "Payment confirmed",
      publicSuccessBody:
        "Your Premium plan will activate when Lemon Squeezy confirms the subscription by webhook. This usually takes a few seconds."
    }
  }
};
