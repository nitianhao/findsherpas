import { ArrowUpRight } from "lucide-react";
import { ReachOutForm } from "@/components/site/reach-out-form";
import { createPageMetadata } from "@/lib/seo";

export const metadata = createPageMetadata({
  title: "Discuss your search",
  description:
    "Tell Find Sherpas about your ecommerce search, your platform and what you want to improve. Start with a conversation.",
  path: "/contact",
});

export default function ContactPage() {
  return (
    <>
      <section className="fs-page-hero">
        <h1>
          What should your
          <br />
          search do better?
        </h1>
        <p>
          A first conversation about your store, your search and where you want
          to take it. You do not need a finished brief.
        </p>
      </section>
      <section className="fs-section fs-contact-layout">
        <div className="fs-contact-intro">
          <h2>Let’s talk it through.</h2>
          <p>
            Book a conversation or send a short message. A little context helps
            us make the discussion useful:
          </p>
          <ul>
            <li>Your store and the markets you serve</li>
            <li>The search platform you use</li>
            <li>What is not working, or what you want to improve</li>
          </ul>
          <a
            className="fs-button"
            href="https://cal.eu/michal-pekarcik-r6j8fb"
            target="_blank"
            rel="noopener noreferrer"
          >
            Choose a time <ArrowUpRight size={20} aria-hidden="true" />
          </a>
          <p className="fs-small">Opens our booking calendar in a new tab.</p>
          <p>Prefer email?</p>
          <a className="fs-contact-email" href="mailto:michal@findsherpas.com">
            michal@findsherpas.com
          </a>
        </div>
        <div className="fs-contact-form">
          <h2>Start with a message.</h2>
          <ReachOutForm />
        </div>
      </section>
      <section className="fs-contact-location" aria-labelledby="contact-location-title">
        <div className="fs-contact-location-copy">
          <h2 id="contact-location-title">Find us in Prague.</h2>
          <p>
            Our Prague address is inside Dům Radost, the functionalist landmark
            beside Winston Churchill Square in Žižkov.
          </p>
          <address>
            <strong>Dům Radost</strong>
            <span>náměstí Winstona Churchilla 1800/2</span>
            <span>130 00 Praha 3 – Žižkov</span>
            <span>Czechia</span>
          </address>
          <a
            className="fs-contact-map-link"
            href="https://www.openstreetmap.org/?mlat=50.0845968&mlon=14.4419771#map=17/50.0845968/14.4419771"
            target="_blank"
            rel="noopener noreferrer"
          >
            Open in OpenStreetMap
            <ArrowUpRight size={19} aria-hidden="true" />
          </a>
        </div>
        <div className="fs-contact-map">
          <iframe
            title="Map showing Dům Radost in Prague 3"
            src="https://www.openstreetmap.org/export/embed.html?bbox=14.4359%2C50.0815%2C14.4480%2C50.0877&layer=mapnik&marker=50.0845968%2C14.4419771"
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
          />
        </div>
      </section>
    </>
  );
}
