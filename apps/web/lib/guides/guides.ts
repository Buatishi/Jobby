import {
  ATS_FORMAT_PENALTIES,
  ATS_KEYWORD_POINTS,
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
          text: "Cuando pedís el análisis ATS en Jobby, tu CV se revisa contra un puesto concreto y desde dos ángulos."
        },
        {
          type: "paragraph",
          text: `El primero son las palabras clave. Jobby toma las habilidades y tecnologías que pide el puesto y mira cuáles aparecen en tu CV. Una coincidencia exacta o una variante conocida, como «API REST» y «REST APIs», suma ${formatPoints(ATS_KEYWORD_POINTS.literal)}; una de significado parecido suma ${formatPoints(ATS_KEYWORD_POINTS.semantic)}.`
        },
        {
          type: "paragraph",
          text: `El segundo es el formato, que le resta puntos al resultado: ${ATS_FORMAT_PENALTIES.TABLES} si el CV tiene tablas, ${ATS_FORMAT_PENALTIES.MULTI_COLUMN} si usa varias columnas, ${ATS_FORMAT_PENALTIES.IMAGES} si tiene imágenes y ${ATS_FORMAT_PENALTIES.NON_STANDARD_HEADERS} si algún título de sección no es de los habituales.`
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
  related: ["palabras-clave-del-cv", "como-adaptar-tu-cv-a-una-oferta"]
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
  related: ["como-adaptar-tu-cv-a-una-oferta", "palabras-clave-del-cv"]
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
          text: "En Jobby cargás tu CV una vez y pegás el puesto. El sistema compara tu perfil con la oferta requisito por requisito y te muestra el match score, qué habilidades coinciden y cuáles faltan, y el análisis ATS. Con eso decidís qué reescribir antes de postularte, y podés repetirlo con cada puesto nuevo."
        }
      ]
    }
  ],
  related: ["palabras-clave-del-cv", "que-es-el-match-score"]
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
  related: ["como-adaptar-tu-cv-a-una-oferta", "que-es-un-ats"]
};

export const GUIDES: Guide[] = [
  queEsUnAts,
  queEsElMatchScore,
  comoAdaptarTuCv,
  palabrasClave
];

export function getGuide(slug: string): Guide | undefined {
  return GUIDES.find((guide) => guide.slug === slug);
}
