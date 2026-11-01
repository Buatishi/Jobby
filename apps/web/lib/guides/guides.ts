import {
  ATS_SCORE_WEIGHTS,
  ATS_KEYWORD_POINTS,
  CV_OPTIMIZATIONS_PER_MONTH,
  FREE_JOB_ANALYSES_PER_MONTH,
  FULL_RELEVANCE_PERCENT,
  GAP_THRESHOLD_PERCENT,
  MATCH_SCORE_WEIGHTS,
  formatPercent,
  formatPoints
} from "@/lib/guides/facts";
import type { Guide } from "@/lib/guides/types";

// Guías en español para búsquedas de quien todavía no conoce Jobby. Reglas de redacción:
// ninguna cifra de mercado ni promesa de resultado, y toda cifra del producto sale de `facts.ts`.

const topWeights = MATCH_SCORE_WEIGHTS[0].percent + MATCH_SCORE_WEIGHTS[1].percent;

const queEsUnAts: Guide = {
  slug: "que-es-un-ats",
  title: "Qué es un ATS y cómo lee tu CV",
  seoTitle: "Qué es un ATS y cómo lee tu CV | Jobby",
  description:
    "Qué es un sistema de seguimiento de candidatos (ATS), qué hace con tu CV y qué formato le facilita la lectura. Guía práctica en español.",
  intro:
    "ATS son las siglas de applicant tracking system, un sistema de seguimiento de candidatos. Es el software con el que muchas empresas reciben, ordenan y consultan las postulaciones a un puesto. Entender cómo lo usa un equipo de selección te ayuda a armar un CV que se lea bien tanto por el sistema como por una persona.",
  sections: [
    {
      heading: "Qué hace un ATS",
      blocks: [
        {
          type: "paragraph",
          text: "Cada empresa lo configura a su manera y existen muchos productos distintos, así que no hay un único criterio. En general, un ATS hace estas cosas:"
        },
        {
          type: "list",
          items: [
            "Reúne en un solo lugar las postulaciones que llegan por la web de empleo, por correo o desde un portal.",
            "Lee el archivo del CV y pasa su contenido a campos: datos de contacto, experiencia, estudios, habilidades e idiomas.",
            "Permite buscar y filtrar entre muchas postulaciones, por ejemplo por una tecnología, un título o una ciudad.",
            "Ordena el proceso en etapas, como preselección, entrevistas y oferta, y deja registro de quién hizo qué.",
            "Algunos productos muestran un puntaje de afinidad entre la postulación y la oferta. Es una ayuda para ordenar, y la forma de calcularlo cambia de un sistema a otro."
          ]
        }
      ]
    },
    {
      heading: "¿Un robot descarta tu CV?",
      blocks: [
        {
          type: "paragraph",
          text: "Es una idea muy repetida, pero conviene matizarla. En muchos procesos la decisión la toma una persona, y el ATS le sirve para organizar y buscar. Lo que sí pasa es que quien selecciona suele tener muchas postulaciones para un mismo puesto y busca por términos concretos."
        },
        {
          type: "paragraph",
          text: "También existen filtros que fija la empresa, como preguntas obligatorias sobre autorización de trabajo, ubicación o un requisito excluyente. Si la respuesta no cumple, la postulación puede quedar fuera, y eso depende de cómo armó el proceso cada empresa."
        },
        {
          type: "paragraph",
          text: "La conclusión práctica es doble: que tu CV se lea sin errores en el sistema y que contenga los términos que la oferta usa para describir lo que busca. Así es más fácil que aparezca cuando alguien busca."
        }
      ]
    },
    {
      heading: "Cómo lee un ATS tu CV",
      blocks: [
        {
          type: "paragraph",
          text: "Para leer el archivo, el sistema lo convierte en texto y trata de reconocer las secciones, las fechas y los cargos. Ese proceso se llama parseo, y falla con más facilidad cuando el documento se aleja de una estructura simple. Estos son los problemas más comunes:"
        },
        {
          type: "list",
          items: [
            "Texto dentro de imágenes: si el contenido es una imagen, el sistema no lo puede leer como texto.",
            "Tablas y varias columnas: el orden de lectura puede mezclarse y una fecha terminar al lado de otro cargo.",
            "Nombres de sección poco comunes, como «Mi recorrido» en lugar de «Experiencia»: el sistema puede no saber qué es cada bloque.",
            "Datos importantes en el encabezado o en el pie del documento: algunos sistemas no los leen.",
            "Íconos, barras o estrellas de nivel y tipografías decorativas, que no aportan información en texto."
          ]
        }
      ]
    },
    {
      heading: "Formato que facilita la lectura",
      blocks: [
        {
          type: "list",
          items: [
            "Una sola columna, con el contenido en orden de lectura de arriba hacia abajo.",
            "Secciones con nombres habituales: Experiencia, Educación, Habilidades, Idiomas y Certificaciones.",
            "Un archivo con texto seleccionable. Si podés marcar y copiar el texto del PDF, un sistema también puede leerlo.",
            "Fechas escritas siempre igual, por ejemplo mes y año, y cargos con el nombre del puesto y el de la empresa.",
            "Tus datos de contacto en el cuerpo del documento y no solo en el encabezado.",
            "Si la oferta pide un formato de archivo, por ejemplo .docx, respetalo."
          ]
        }
      ]
    },
    {
      heading: "Qué revisa el análisis ATS de Jobby",
      blocks: [
        {
          type: "paragraph",
          text: "Cuando pedís el análisis ATS en Jobby, tu CV se revisa contra un puesto concreto desde tres ángulos: las palabras clave, los requisitos del puesto y la lectura del archivo."
        },
        {
          type: "paragraph",
          text: `El primero son las palabras clave. Jobby toma las habilidades y tecnologías que pide el puesto y mira cuáles aparecen en tu CV. Una coincidencia exacta o una variante conocida, como «API REST» y «REST APIs», suma ${formatPoints(ATS_KEYWORD_POINTS.literal)}; una de significado parecido suma ${formatPoints(ATS_KEYWORD_POINTS.semantic)}.`
        },
        {
          type: "paragraph",
          text: "El segundo son los requisitos del puesto: los años de experiencia, la formación y los idiomas que pide. Los años salen solo de puestos de trabajo (freelance, por cuenta propia, en una pyme o en una empresa) y solo cuenta la experiencia directa con lo que pide el puesto. No hace falta cumplir lo pedido al pie de la letra: si lo superás, cuenta como cumplido y se aclara aparte, sin sumar ni restar."
        },
        {
          type: "paragraph",
          text: `El puntaje combina las palabras clave (${ATS_SCORE_WEIGHTS.skills} %), los años (${ATS_SCORE_WEIGHTS.experience} %), la formación (${ATS_SCORE_WEIGHTS.education} %) y los idiomas (${ATS_SCORE_WEIGHTS.languages} %). Lo que el puesto no pide no entra, y su peso se reparte entre el resto.`
        },
        {
          type: "paragraph",
          text: "El tercero es la lectura del archivo. Jobby te avisa si el CV tiene tablas, varias columnas, imágenes o títulos de sección poco habituales, porque no todos los sistemas leen igual esos recursos. Es un aviso: no resta puntos."
        },
        {
          type: "paragraph",
          text: "Son criterios de Jobby, pensados como una guía práctica. No son las reglas de un ATS en particular, y cada empresa usa uno distinto."
        }
      ]
    },
    {
      heading: "Lista rápida antes de postularte",
      blocks: [
        {
          type: "list",
          items: [
            "Copiá el contenido de tu CV en un bloc de notas y fijate si el orden y las secciones se mantienen.",
            "Compará los términos de tu CV con los de la oferta y usá los mismos cuando describan algo que de verdad hiciste.",
            "Sacá las tablas, las columnas y las imágenes que no aporten.",
            "Revisá que cada sección tenga un nombre habitual.",
            "Guardá una versión base y adaptala para cada puesto."
          ]
        }
      ]
    }
  ],
  related: [
    "palabras-clave-del-cv",
    "como-adaptar-tu-cv-a-una-oferta",
    "cv-compatible-con-ats"
  ]
};

const queEsElMatchScore: Guide = {
  slug: "que-es-el-match-score",
  title: "Qué es el match score y cómo se calcula",
  seoTitle: "Qué es el match score de un CV y cómo se calcula | Jobby",
  description:
    "El match score mide cuánto coincide tu CV con un puesto. Así lo calcula Jobby: seis componentes con su peso, qué significa el resultado y cómo mejorarlo.",
  intro:
    "El match score es un número de 0 a 100 que resume cuánto de lo que pide un puesto aparece en tu perfil. No predice si te van a contratar: sirve para ver qué tan cerca estás de la oferta y dónde están las diferencias.",
  sections: [
    {
      heading: "Qué mide y qué no",
      blocks: [
        {
          type: "paragraph",
          text: "Mide la coincidencia entre dos cosas: lo que dice tu perfil y lo que dice la oferta. No mide tu valor profesional ni anticipa la decisión de quien selecciona, que además mira cosas que ningún cálculo ve."
        },
        {
          type: "paragraph",
          text: "Tampoco hay una fórmula única. Cada herramienta pondera distinto, así que el mismo CV puede dar números diferentes en dos servicios. Lo útil es entender de qué está hecho el número que ves."
        }
      ]
    },
    {
      heading: "Cómo lo calcula Jobby: seis componentes",
      blocks: [
        {
          type: "paragraph",
          text: "Jobby combina seis componentes y cada uno tiene su peso. Sumados dan el 100 %:"
        },
        {
          type: "list",
          items: MATCH_SCORE_WEIGHTS.map(
            (weight) =>
              `${weight.label} (${formatPercent(weight.percent)}): ${weight.detail}`
          )
        },
        {
          type: "paragraph",
          text: `Por eso las habilidades y el nivel de experiencia juntos pesan el ${formatPercent(topWeights)} del resultado, y los idiomas, los estudios y las habilidades blandas completan el resto.`
        }
      ]
    },
    {
      heading: "La relevancia del área",
      blocks: [
        {
          type: "paragraph",
          text: "Antes de mostrarte el resultado, Jobby lo ajusta por la relevancia del puesto para tu área. Sin este ajuste, un CV de sistemas contra un puesto de cocina sumaría puntos solo porque la oferta no pide inglés o porque coincide la modalidad."
        },
        {
          type: "paragraph",
          text: `La relevancia mide cuánto de lo que pide el puesto cae en lo que sabés hacer. Cuando al menos el ${formatPercent(FULL_RELEVANCE_PERCENT)} de las habilidades pedidas está en tu perfil, el puesto se considera de tu área y el puntaje no se toca. Por debajo de eso se atenúa, y cuanto menos coincida, más baja.`
        },
        {
          type: "paragraph",
          text: "Una habilidad cuenta si está en tu lista de habilidades o si tu perfil la nombra en el titular, el resumen, los cargos o los logros."
        }
      ]
    },
    {
      heading: "Match y potencial",
      blocks: [
        {
          type: "paragraph",
          text: "Jobby muestra además un puntaje de potencial: el que tendrías si cubrieras las habilidades que te faltan. La diferencia entre el match y el potencial te dice cuánto del resultado depende solo de las habilidades."
        },
        {
          type: "paragraph",
          text: `También indica el origen de la brecha. Si el componente de habilidades o el de seniority queda por debajo del ${formatPercent(GAP_THRESHOLD_PERCENT)}, se marca como parte de la diferencia: habilidades, seniority o ambos.`
        }
      ]
    },
    {
      heading: "Cómo leer el resultado",
      blocks: [
        {
          type: "list",
          items: [
            "Usalo para comparar puestos entre sí y decidir a cuáles te conviene postularte primero.",
            "Mirá el detalle por componente: un resultado bajo por falta de inglés se resuelve distinto que uno por nivel de experiencia.",
            "No le des peso a diferencias de uno o dos puntos entre dos puestos.",
            "No lo tomes como un veredicto: no incluye lo que se ve en una entrevista ni lo que tu perfil no dice."
          ]
        }
      ]
    },
    {
      heading: "Cómo mejorarlo sin inflarlo",
      blocks: [
        {
          type: "list",
          items: [
            "Completá tu perfil con las habilidades que de verdad tenés, incluso las que tu CV no menciona.",
            "Describí tus logros con los términos de la oferta cuando sea cierto.",
            "Cargá tus idiomas con su nivel y tus certificaciones.",
            "Elegí puestos de tu área: ninguna redacción compensa una oferta que pide otra cosa.",
            "No sumes habilidades que no tenés: el puntaje sube, pero la entrevista lo desmiente."
          ]
        }
      ]
    }
  ],
  related: [
    "como-adaptar-tu-cv-a-una-oferta",
    "palabras-clave-del-cv",
    "habilidades-para-poner-en-el-cv"
  ]
};

const comoAdaptarTuCv: Guide = {
  slug: "como-adaptar-tu-cv-a-una-oferta",
  title: "Cómo adaptar tu CV a cada oferta",
  seoTitle: "Cómo adaptar tu CV a una oferta de trabajo | Jobby",
  description:
    "Cómo adaptar tu CV a cada oferta paso a paso: qué leer en el aviso, qué reescribir, qué no inventar y cómo comprobar que quedó alineado.",
  intro:
    "Mandar el mismo CV a todos los puestos es lo más cómodo, y suele ser lo que menos rinde. Adaptarlo no es reescribirlo desde cero ni inventar experiencia: es mostrar, de lo que ya hiciste, lo que esa oferta en particular pide.",
  sections: [
    {
      heading: "Por qué conviene adaptarlo",
      blocks: [
        {
          type: "paragraph",
          text: "Quien selecciona revisa muchas postulaciones y se hace una pregunta simple: ¿esta persona hace lo que necesito? Cuanto más fácil le hagas ver esa respuesta, mejor."
        },
        {
          type: "paragraph",
          text: "Además, si en el proceso interviene una búsqueda por términos o un sistema de seguimiento, usar las palabras de la oferta ayuda a que tu CV aparezca entre los resultados."
        }
      ]
    },
    {
      heading: "Paso a paso",
      blocks: [
        {
          type: "steps",
          items: [
            "Leé la oferta completa y separá lo obligatorio de lo deseable. Suele estar marcado con expresiones como «requisitos», «excluyente» o «se valorará».",
            "Armá una lista con lo que pide: herramientas y tecnologías, años de experiencia, estudios, idiomas, modalidad y responsabilidades del puesto.",
            "Marcá al lado de cada ítem si lo tenés, si lo tenés en parte o si no lo tenés.",
            "Reescribí el resumen del principio para que diga, en dos o tres líneas, por qué encajás con este puesto.",
            "Subí a los primeros lugares la experiencia y los logros más cercanos a lo que pide la oferta.",
            "Contá los logros con números cuando los tengas: qué hiciste, con qué y qué cambió.",
            "Usá el vocabulario de la oferta para describir lo que de verdad hiciste. Si el aviso dice «API REST» y vos escribías «servicios web», conviene nombrarlo como lo nombra la oferta.",
            "Revisá el formato y la coherencia de las fechas, y guardá el archivo con un nombre que indique el puesto."
          ]
        }
      ]
    },
    {
      heading: "Qué no hacer",
      blocks: [
        {
          type: "list",
          items: [
            "No inventes experiencia, títulos ni herramientas. Se descubre en la entrevista y puede costarte la postulación.",
            "No copies párrafos enteros de la oferta: suena a plantilla.",
            "No llenes el CV de palabras sueltas ni escondas texto con el color del fondo. Puede detectarse y juega en contra.",
            "No borres experiencia valiosa solo porque no aparece en la oferta: acortala."
          ]
        }
      ]
    },
    {
      heading: "Qué hacer con lo que no tenés",
      blocks: [
        {
          type: "paragraph",
          text: "Es normal no cumplir todo. Lo que pide una oferta suele ser una lista ideal, y conviene separar tres casos:"
        },
        {
          type: "list",
          items: [
            "Lo que tenés con otro nombre: nombralo como lo nombra la oferta.",
            "Lo que tenés en parte: describí lo que hiciste, con su alcance real, sin exagerar el nivel.",
            "Lo que no tenés: no lo incluyas. Si es un requisito obligatorio, evaluá si la postulación tiene sentido; si es deseable, podés contar en la carta que lo estás aprendiendo."
          ]
        }
      ]
    },
    {
      heading: "Cómo comprobarlo con Jobby",
      blocks: [
        {
          type: "paragraph",
          text: "En Jobby cargás tu CV una vez y pegás el puesto. El sistema compara tu perfil con la oferta y te muestra el match score con su detalle y recomendaciones, y un reporte ATS que marca qué palabras clave del puesto están en tu CV y cuáles faltan. Con eso decidís qué reescribir antes de postularte, y podés repetirlo con cada puesto nuevo."
        }
      ]
    }
  ],
  related: [
    "palabras-clave-del-cv",
    "que-es-el-match-score",
    "optimizar-cv-con-ia"
  ]
};

const palabrasClave: Guide = {
  slug: "palabras-clave-del-cv",
  title: "Palabras clave del CV: cómo elegirlas y dónde usarlas",
  seoTitle: "Palabras clave para el CV: cómo elegirlas | Jobby",
  description:
    "Cómo encontrar las palabras clave de una oferta, cómo escribirlas en tu CV sin llenarlo de términos sueltos y cómo cuenta cada coincidencia en Jobby.",
  intro:
    "Las palabras clave son los términos con los que una oferta describe lo que busca: herramientas, tecnologías, metodologías, títulos y certificaciones. Quien selecciona, y también cualquier sistema que busque por texto, las usa para encontrar candidatos. Tu CV tiene que contenerlas, de forma natural y solo cuando sean ciertas.",
  sections: [
    {
      heading: "De dónde sacarlas",
      blocks: [
        {
          type: "list",
          items: [
            "De la oferta que tenés enfrente: las secciones de requisitos y de responsabilidades.",
            "De los términos que se repiten: si la oferta menciona varias veces un mismo concepto, es importante.",
            "De varias ofertas del mismo rol: lo que aparece en todas es el vocabulario habitual del rubro.",
            "Del título del puesto: el nombre con el que se llama tu rol, que a veces cambia de una empresa a otra."
          ]
        }
      ]
    },
    {
      heading: "Qué tipo de palabras cuentan",
      blocks: [
        {
          type: "list",
          items: [
            "Herramientas y tecnologías: Excel, SQL, React, SAP, Figma.",
            "Metodologías y prácticas: Scrum, gestión de proyectos, testing, atención al cliente.",
            "Títulos, estudios y certificaciones, escritos completos la primera vez.",
            "Idiomas, con su nivel.",
            "Las palabras generales, como «responsable» o «proactivo», pesan poco: describí con hechos lo que hiciste."
          ]
        }
      ]
    },
    {
      heading: "Variantes, siglas y traducciones",
      blocks: [
        {
          type: "paragraph",
          text: "Una misma habilidad se escribe de muchas maneras. «API REST» y «REST APIs» son lo mismo; también JavaScript y JS, o «gestión de proyectos» y «project management». Si no sabés cuál usa la empresa, mirá cómo lo escribe la oferta y usá esa forma. En la sección de habilidades podés sumar la variante."
        },
        {
          type: "paragraph",
          text: "Con las siglas, escribí la forma completa la primera vez y la sigla entre paréntesis, por ejemplo «Applicant Tracking System (ATS)»."
        },
        {
          type: "paragraph",
          text: "Ojo con los nombres parecidos que no son lo mismo: Java no es JavaScript, ni React es React Native. Anotá solo el que usás."
        }
      ]
    },
    {
      heading: "Dónde ponerlas",
      blocks: [
        {
          type: "list",
          items: [
            "En la sección de habilidades, agrupadas y fáciles de leer.",
            "Dentro de los logros de cada experiencia, con contexto, por ejemplo: «Automaticé el reporte mensual con SQL y Excel».",
            "En el resumen inicial, las dos o tres más importantes para ese puesto."
          ]
        },
        {
          type: "paragraph",
          text: "Un término que aparece en la lista de habilidades y también en un logro con contexto dice más que uno que aparece una sola vez."
        }
      ]
    },
    {
      heading: "Qué evitar",
      blocks: [
        {
          type: "list",
          items: [
            "Repetir la misma palabra muchas veces sin sentido.",
            "Escribir texto invisible o escondido con el color del fondo.",
            "Anotar habilidades que no tenés o que no podrías explicar en una entrevista.",
            "Armar listas enormes de herramientas sin ningún contexto."
          ]
        }
      ]
    },
    {
      heading: "Cómo las cuenta Jobby",
      blocks: [
        {
          type: "paragraph",
          text: `En el análisis ATS, Jobby toma las habilidades y tecnologías del puesto como palabras clave y marca cada una según cómo aparece en tu CV. Una coincidencia exacta o una variante conocida, es decir, un alias o una traducción como «API REST» y «REST APIs», suma ${formatPoints(ATS_KEYWORD_POINTS.literal)}. Una coincidencia de significado parecido suma ${formatPoints(ATS_KEYWORD_POINTS.semantic)}. Lo que no aparece no suma.`
        },
        {
          type: "paragraph",
          text: "Eso significa que escribir una habilidad con el nombre exacto que usa la oferta es la forma más segura de que cuente entera."
        }
      ]
    }
  ],
  related: [
    "como-adaptar-tu-cv-a-una-oferta",
    "que-es-un-ats",
    "analizar-cv-con-ia"
  ]
};

const cvCompatibleConAts: Guide = {
  slug: "cv-compatible-con-ats",
  title: "Cómo hacer un CV compatible con ATS",
  seoTitle: "CV compatible con ATS: lista de control | Jobby",
  description:
    "Lista de control para que un sistema de seguimiento de candidatos lea bien tu CV: formato, títulos, fechas, archivo y plantillas, con ejemplos.",
  intro:
    "Un CV compatible con ATS no es un CV feo ni uno sin personalidad. Es un CV cuyo contenido se puede leer como texto y donde cada dato está en el lugar en que un sistema espera encontrarlo. Esta guía es una lista de control con ejemplos para revisar el tuyo antes de postularte. Si primero querés entender qué es un ATS y cómo lo usa un equipo de selección, empezá por la guía «Qué es un ATS y cómo lee tu CV».",
  sections: [
    {
      heading: "Los puntos que conviene revisar",
      blocks: [
        {
          type: "list",
          items: [
            "Una sola columna. Con dos columnas, el sistema puede leer una línea de cada lado y mezclar una fecha con el cargo equivocado.",
            "Sin tablas para ordenar el contenido. Una tabla que se ve prolija puede convertirse en texto desordenado al leerla.",
            "Sin imágenes que contengan información. Si tu experiencia o tus habilidades están dentro de una imagen, el sistema no las puede leer como texto.",
            "Títulos de sección habituales, como Experiencia, Educación, Habilidades e Idiomas.",
            "Fechas escritas siempre igual y cargos siempre en el mismo orden.",
            "Datos de contacto en el cuerpo del documento, no solo en el encabezado o en el pie.",
            "Un archivo con texto seleccionable, no una foto ni un escaneo de tu CV."
          ]
        }
      ]
    },
    {
      heading: "Ejemplos: qué escribir y qué evitar",
      blocks: [
        {
          type: "list",
          items: [
            "Títulos: «Experiencia laboral» en lugar de «Mi recorrido»; «Educación» en lugar de «Dónde aprendí»; «Habilidades» en lugar de «Mis superpoderes».",
            "Fechas: «03/2022 – 08/2024» o «marzo 2022 – agosto 2024», pero sin mezclar los dos estilos en el mismo CV.",
            "Cargos: «Analista de datos, Empresa X, 03/2022 – 08/2024», con el mismo orden en todos los puestos.",
            "Habilidades: «Python, SQL, Power BI» escrito como texto, en lugar de tres barras de nivel dibujadas.",
            "Contacto: tu correo y tu teléfono escritos en el cuerpo del documento, y no solo como íconos en un costado."
          ]
        }
      ]
    },
    {
      heading: "Un diseño cuidado que se siga leyendo bien",
      blocks: [
        {
          type: "paragraph",
          text: "Que un sistema pueda leer tu CV no obliga a que sea una página gris. Se puede lograr un buen aspecto con recursos que no rompen la lectura:"
        },
        {
          type: "list",
          items: [
            "Jerarquía con negritas y tamaños de letra distintos para los títulos, en lugar de columnas o recuadros.",
            "Espacios en blanco entre secciones para que respire.",
            "Viñetas simples para los logros de cada puesto.",
            "Una sola tipografía común y legible, con un color de acento como máximo."
          ]
        }
      ]
    },
    {
      heading: "Plantillas: cómo elegir una",
      blocks: [
        {
          type: "paragraph",
          text: "Muchas plantillas vienen con columnas, íconos y barras de nivel de fábrica. Antes de usar una, hacé esta prueba de tres minutos:"
        },
        {
          type: "steps",
          items: [
            "Guardá tu CV en el formato en que lo vas a enviar.",
            "Abrí el archivo, seleccioná todo el texto y copialo.",
            "Pegalo en un bloc de notas.",
            "Fijate que las secciones sigan en orden, que cada cargo conserve su fecha y que no falte nada que estuviera en el encabezado.",
            "Si el texto sale mezclado o incompleto, elegí otra plantilla o simplificá esta."
          ]
        }
      ]
    },
    {
      heading: "Cómo revisarlo con Jobby",
      blocks: [
        {
          type: "paragraph",
          text: `En el análisis ATS de Jobby, el formato no resta puntos: el reporte te avisa si el CV tiene tablas, varias columnas, imágenes o títulos de sección poco habituales, para que decidas si conviene cambiarlo. También te muestra qué palabras clave del puesto aparecen en tu CV y cuáles no, y si cumplís los años, la formación y los idiomas que pide.`
        },
        {
          type: "paragraph",
          text: "Son criterios de Jobby, pensados como una guía práctica, y no las reglas de un ATS en particular: cada empresa usa uno distinto. Un CV que se lee bien es una condición necesaria, pero no suficiente, porque la decisión final siempre es de la empresa."
        }
      ]
    }
  ],
  related: ["que-es-un-ats", "palabras-clave-del-cv", "analizar-cv-con-ia"]
};

const analizarCvConIa: Guide = {
  slug: "analizar-cv-con-ia",
  title: "Analizar tu CV con IA: qué puede decirte y qué no",
  seoTitle: "Analizar tu CV con IA: qué esperar | Jobby",
  description:
    "Qué puede analizar una herramienta de IA en tu CV, cómo leer el resultado y qué límites tiene. Con el ejemplo de cómo lo hace Jobby.",
  intro:
    "Analizar el CV con inteligencia artificial sirve para mirarlo como lo haría alguien que no te conoce: qué entiende, qué le falta y qué no encaja con un puesto. Es una ayuda para decidir qué corregir, no un veredicto. Esta guía explica qué se puede analizar, cómo leer un resultado y qué límites tiene.",
  sections: [
    {
      heading: "Qué puede analizar una herramienta",
      blocks: [
        {
          type: "list",
          items: [
            "El formato: si el archivo se puede leer como texto y si la estructura es simple.",
            "Las secciones: si están las habituales y si los títulos se reconocen.",
            "Las palabras clave: qué términos de la oferta aparecen en tu CV, tal cual o con otro nombre.",
            "Los requisitos: tus habilidades, tu nivel de experiencia, tus idiomas y tus estudios frente a lo que pide el puesto.",
            "La coherencia: si los cargos y las fechas del CV coinciden con los de tu perfil de LinkedIn."
          ]
        }
      ]
    },
    {
      heading: "Con puesto o sin puesto",
      blocks: [
        {
          type: "paragraph",
          text: "Un análisis sin puesto solo puede opinar sobre el formato y la claridad del documento. Para saber si tu CV encaja hace falta una oferta concreta, porque lo que «falta» depende de lo que esa oferta pide."
        },
        {
          type: "paragraph",
          text: "Por eso conviene analizar el CV contra los puestos a los que de verdad pensás postularte, y no contra uno genérico."
        }
      ]
    },
    {
      heading: "Cómo leer el resultado",
      blocks: [
        {
          type: "steps",
          items: [
            "Mirá primero qué requisitos faltan, antes que el número. El detalle te dice qué corregir; el número solo lo resume.",
            "Distinguí lo que no tenés de lo que tenés con otro nombre. Si la oferta dice «API REST» y tu CV dice «servicios web», lo que cambia es la redacción, no tu experiencia.",
            "Revisá cada recomendación y quedate con las que son ciertas para vos. Una herramienta no conoce tu historia completa.",
            "Corregí el CV y repetí el análisis con el mismo puesto para ver qué cambió.",
            "Repetilo con otros puestos. Un puntaje sirve para comparar ofertas entre sí y decidir dónde conviene postularte primero."
          ]
        },
        {
          type: "paragraph",
          text: "Un puntaje no mide tu valor como profesional. Mide cuánto se parece tu CV, tal como está escrito hoy, a lo que pide una oferta."
        }
      ]
    },
    {
      heading: "Límites que conviene tener presentes",
      blocks: [
        {
          type: "list",
          items: [
            "Una IA puede interpretar mal un dato o pasar por alto un matiz.",
            "No conoce el sistema de selección de cada empresa ni cómo decide la persona que revisa.",
            "No reemplaza que alguien de confianza lea tu CV.",
            "Un buen resultado no asegura que te llamen: la decisión es de la empresa.",
            "Tu CV tiene datos personales. Antes de subirlo a una herramienta, leé qué hace con ellos."
          ]
        }
      ]
    },
    {
      heading: "Cómo lo hace Jobby",
      blocks: [
        {
          type: "paragraph",
          text: `En Jobby cargás tu CV una vez y pegás el puesto. El análisis devuelve un match score de 0 a 100 con el detalle de sus seis componentes y recomendaciones priorizadas, y un reporte ATS que marca cada palabra clave del puesto como presente (✓), parecida (~) o faltante (✗) y revisa el formato. El plan gratis incluye ${FREE_JOB_ANALYSES_PER_MONTH} análisis de puestos por mes.`
        },
        {
          type: "paragraph",
          text: "El equipo de administración de Jobby solo ve métricas agregadas, nunca el contenido de tu CV."
        }
      ]
    }
  ],
  related: [
    "que-es-el-match-score",
    "cv-compatible-con-ats",
    "optimizar-cv-con-ia"
  ]
};

const optimizarCvConIa: Guide = {
  slug: "optimizar-cv-con-ia",
  title: "Optimizar el CV con IA sin inventar experiencia",
  seoTitle: "Optimizar el CV con IA sin inventar | Jobby",
  description:
    "Cómo usar IA para reescribir tu CV para un puesto sin sumar experiencia que no tenés: qué pedir, qué revisar y cómo comprobar las palabras clave.",
  intro:
    "Pedirle a una IA que mejore tu CV para un puesto puede ahorrarte horas, pero tiene un riesgo conocido: los modelos de lenguaje tienden a completar. Si algo falta, pueden escribir una cifra, una herramienta o una empresa que nunca existieron. Optimizar tiene que ser reordenar y reformular lo que ya hiciste, no sumar lo que no hiciste. Esta guía explica cómo usar la IA sin inventar, qué revisar y cómo lo resuelve Jobby.",
  sections: [
    {
      heading: "Qué sí y qué no conviene pedirle",
      blocks: [
        {
          type: "paragraph",
          text: "La IA es buena para reformular y ordenar, y no puede saber qué hiciste vos. Conviene pedirle que:"
        },
        {
          type: "list",
          items: [
            "Reformule tus logros con verbos de acción y más claridad.",
            "Ponga primero la experiencia más cercana al puesto.",
            "Use el vocabulario de la oferta para describir lo que de verdad hiciste.",
            "Acorte los párrafos largos."
          ]
        },
        {
          type: "paragraph",
          text: "Y conviene no dejar que:"
        },
        {
          type: "list",
          items: [
            "Invente cifras, porcentajes o plazos.",
            "Sume empresas, cargos, títulos o fechas.",
            "Agregue herramientas que no usaste.",
            "Exagere el nivel de lo que hiciste."
          ]
        }
      ]
    },
    {
      heading: "Cómo pedírselo",
      blocks: [
        {
          type: "steps",
          items: [
            "Pasale tu CV completo y la oferta, así trabaja con el contexto real.",
            "Escribí la regla de forma explícita: «Trabajá solo con lo que está en mi CV. No agregues experiencia, empresas, fechas ni cifras».",
            "Pedile una sección por vez, para poder revisar cada cambio.",
            "Pedile que indique qué cambió en cada sección y por qué.",
            "Si el resultado trae un dato que no es tuyo, borralo o pedí otra versión."
          ]
        }
      ]
    },
    {
      heading: "Qué revisar antes de usar el resultado",
      blocks: [
        {
          type: "list",
          items: [
            "Cada cifra, fecha y nombre propio, contra tu CV original.",
            "Cada herramienta o tecnología nombrada: ¿la usaste de verdad?",
            "Que el nivel que sugiere sea el real.",
            "Que suene a vos y no a una copia del aviso.",
            "Que no se repitan las mismas frases en distintas secciones."
          ]
        }
      ]
    },
    {
      heading: "La trampa de las palabras clave",
      blocks: [
        {
          type: "paragraph",
          text: "Cuando una IA lee la oferta, tiende a incluir sus palabras clave en tu CV aunque no figuren en tu experiencia. El CV puede verse más alineado, pero te deja expuesto: si escribís una herramienta que nunca usaste, una pregunta en la entrevista alcanza para dejarlo en evidencia."
        },
        {
          type: "paragraph",
          text: "La regla práctica es simple: una palabra clave entra al CV solo si podés contar en una entrevista dónde y cómo la usaste."
        }
      ]
    },
    {
      heading: "Cómo lo hace Jobby",
      blocks: [
        {
          type: "paragraph",
          text: "El CV Optimizer de Jobby reescribe las secciones de tu CV que cubren poco lo que pide un puesto. Al hacerlo le pide a la IA que trabaje con lo que ya está en tu CV, sin sumar experiencia, empresas ni fechas."
        },
        {
          type: "paragraph",
          text: "Después cruza el texto nuevo con el análisis ATS de tu CV. Si el texto menciona una palabra clave que tu CV no respalda, la muestra como «Sin respaldo en tu CV», con el aviso de usarla solo si de verdad tenés esa experiencia. El puntaje ATS que muestra, antes y después, cuenta solo lo que tu CV respalda."
        },
        {
          type: "paragraph",
          text: `Podés descargar el CV optimizado en PDF, en una sola columna. El plan gratis incluye ${CV_OPTIMIZATIONS_PER_MONTH.free} optimizaciones por mes y el premium, ${CV_OPTIMIZATIONS_PER_MONTH.premium}. La revisión final es siempre tuya: leé el texto nuevo contra tu CV antes de enviarlo.`
        }
      ]
    }
  ],
  related: [
    "como-adaptar-tu-cv-a-una-oferta",
    "palabras-clave-del-cv",
    "analizar-cv-con-ia"
  ]
};

const habilidadesParaElCv: Guide = {
  slug: "habilidades-para-poner-en-el-cv",
  title: "Qué habilidades poner en el CV y cómo ordenarlas",
  seoTitle: "Qué habilidades poner en el CV | Jobby",
  description:
    "Qué habilidades incluir en tu CV, cómo separar las técnicas de las blandas, mostrar el nivel y cuánto pesan en el match score de Jobby.",
  intro:
    "La sección de habilidades suele ser la más leída y la peor armada: listas largas, sin orden y sin nada que las respalde. Una buena lista es corta, está ordenada según lo que pide el puesto y cada ítem se apoya en tu experiencia. Esta guía te ayuda a elegir qué incluir, cómo mostrar el nivel y qué peso tienen en el match score.",
  sections: [
    {
      heading: "Habilidades técnicas y blandas",
      blocks: [
        {
          type: "paragraph",
          text: "Las habilidades técnicas, o duras, se pueden enseñar y comprobar: herramientas, tecnologías, métodos e idiomas. Las blandas son formas de trabajar con otras personas, como la comunicación, el liderazgo o la organización."
        },
        {
          type: "list",
          items: [
            "Técnicas, por ejemplo: Python, SQL, Excel avanzado, contabilidad de costos, diseño en Figma.",
            "Blandas, por ejemplo: comunicación, trabajo en equipo, liderazgo, resolución de problemas."
          ]
        },
        {
          type: "paragraph",
          text: "Las técnicas van bien en una lista. Las blandas funcionan mejor cuando se ven en tus logros: «Coordiné con tres áreas la migración del sistema de turnos» dice más sobre coordinación que la palabra «liderazgo» suelta en una lista."
        }
      ]
    },
    {
      heading: "Cómo elegir cuáles incluir",
      blocks: [
        {
          type: "steps",
          items: [
            "Leé la oferta y subrayá las habilidades que pide.",
            "Escribí al lado cuáles usaste de verdad y dónde.",
            "Incluí las que podés defender en una entrevista con un ejemplo concreto.",
            "Ordená la lista poniendo primero las que la oferta menciona más o marca como obligatorias.",
            "Sacá las que ya no usás y las que no aportan al puesto."
          ]
        }
      ]
    },
    {
      heading: "Cómo mostrar el nivel",
      blocks: [
        {
          type: "paragraph",
          text: "Las barras, las estrellas y los puntos de nivel no dicen cuánto sabés, y un sistema de lectura no los interpreta como texto. Hay formas más claras de mostrarlo:"
        },
        {
          type: "list",
          items: [
            "Agrupar por nivel: «Uso diario: Python, SQL. Conocimiento básico: Docker».",
            "Sumar el tiempo o el contexto de uso: «Excel avanzado: tablas dinámicas y macros, 4 años».",
            "Indicar el idioma con una escala conocida, como B2 del marco europeo, o con palabras claras: básico, intermedio o avanzado."
          ]
        }
      ]
    },
    {
      heading: "Cuánto pesan en el match score",
      blocks: [
        {
          type: "paragraph",
          text: `En el match score de Jobby, las habilidades son el componente de mayor peso: ${MATCH_SCORE_WEIGHTS[0].label} (${formatPercent(MATCH_SCORE_WEIGHTS[0].percent)}). Jobby cuenta cuántas de las que pide el puesto están en tu perfil, incluidas las variantes conocidas y las de significado parecido.`
        },
        {
          type: "paragraph",
          text: `Las ${MATCH_SCORE_WEIGHTS[5].label.toLowerCase()} pesan ${formatPercent(MATCH_SCORE_WEIGHTS[5].percent)}. Se detectan en la descripción y en los logros de tu experiencia, y por eso conviene mostrarlas ahí. Esos pesos son criterios de Jobby, no una regla general del mercado.`
        }
      ]
    },
    {
      heading: "Errores frecuentes",
      blocks: [
        {
          type: "list",
          items: [
            "Listas de decenas de ítems, que diluyen las que de verdad importan.",
            "Habilidades sin ninguna experiencia que las respalde.",
            "Nombrar la misma herramienta de dos formas distintas en distintas partes del CV, sin unirlas.",
            "Mezclar en una misma lista habilidades, tareas y títulos.",
            "Poner primero lo que más te gusta en lugar de lo que más pide el puesto."
          ]
        }
      ]
    }
  ],
  related: [
    "que-es-el-match-score",
    "palabras-clave-del-cv",
    "como-adaptar-tu-cv-a-una-oferta"
  ]
};

export const GUIDES: Guide[] = [
  queEsUnAts,
  queEsElMatchScore,
  comoAdaptarTuCv,
  palabrasClave,
  cvCompatibleConAts,
  analizarCvConIa,
  optimizarCvConIa,
  habilidadesParaElCv
];

export function getGuide(slug: string): Guide | undefined {
  return GUIDES.find((guide) => guide.slug === slug);
}
