import { Helmet } from "react-helmet-async";
import { config } from "@/configs";

export default function Index() {
  return (
    <Helmet>
      <title>Duck Council</title>
      <meta
        name="description"
        content="AI-Powered Reflections for Human Decisions Ask the council. Reflect with ducks. Make better choices."
      />
      <link rel="canonical" href={config.DOMAIN} />

      <meta property="og:url" content={config.DOMAIN} />
      <meta property="og:title" content="Duck Council" />
      <meta
        property="og:description"
        content="AI-Powered Reflections for Human Decisions Ask the council. Reflect with ducks. Make better choices."
      />
      <meta property="og:site_name" content="Duck Council" />

      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:site" content="@site" />
      <meta name="twitter:creator" content="@handle" />
      <meta name="twitter:title" content="Duck Council" />
      <meta
        name="twitter:description"
        content="AI-Powered Reflections for Human Decisions Ask the council. Reflect with ducks. Make better choices."
      />

      <script type="application/ld+json">
        {JSON.stringify({
          "@context": "https://schema.org",
          "@type": "FAQPage",
          mainEntity: [
            {
              "@type": "Question",
              name: "What is the purpose of the Duck Council?",
              acceptedAnswer: {
                "@type": "Answer",
                text: "Humans are emotional. Decisions are messy. But what if you had a council of intelligent ducks to reflect back your choices? ",
              },
            },
            {
              "@type": "Question",
              name: "Is it safe to use the Duck Council?",
              acceptedAnswer: {
                "@type": "Answer",
                text: "Yes, it is safe to use.",
              },
            },
            {
              "@type": "Question",
              name: "What is the cost of the Duck Council?",
              acceptedAnswer: {
                "@type": "Answer",
                text: "$0.00 = Free",
              },
            },
          ],
        })}
      </script>

      <script type="application/ld+json">
        {JSON.stringify({
          "@context": "https://schema.org",
          "@type": "BreadcrumbList",
          itemListElement: [
            {
              "@type": "ListItem",
              position: 1,
              name: "Duck Council",
              item: config.DOMAIN,
            },
          ],
        })}
      </script>

      <script type="application/ld+json">
        {JSON.stringify({
          "@context": "https://schema.org",
          "@type": "Person",
          name: "Jee",
          url: "https://jaenudinv2.vercel.app",
          sameAs: ["https://www.linkedin.com/in/jaenudin-jee-650482199"],
        })}
      </script>
    </Helmet>
  );
}
