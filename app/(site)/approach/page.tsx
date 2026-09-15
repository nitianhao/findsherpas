import { ContactBand } from "@/components/site/contact-band";
import { ApproachIllustration } from "@/components/site/approach-illustration";
import { createPageMetadata } from "@/lib/seo";

export const metadata = createPageMetadata({
  title: "How we work",
  description:
    "From search data and a detailed assessment to prioritized improvements, engineering tickets and ongoing search optimization.",
  path: "/approach",
});

export default function ApproachPage() {
  return (
    <>
      <section className="fs-page-hero">
        <h1>
          A clear first move.
          <br />A plan for what follows.
        </h1>
        <p>
          We start with the search you have, the customers using it and the
          problems worth solving. Then we work with your team to make the
          changes measurable.
        </p>
      </section>
      <section className="fs-section fs-engagement-summary" aria-labelledby="first-engagement-title">
        <h2 id="first-engagement-title">Your first engagement, in practical terms.</h2>
        <dl>
          <div>
            <dt>Before we begin</dt>
            <dd>A short conversation about your store, markets, search platform and what you want to improve.</dd>
          </div>
          <div>
            <dt>What we need</dt>
            <dd>Search query and behaviour data, plus access to the current platform when available.</dd>
          </div>
          <div>
            <dt>What you receive</dt>
            <dd>A prioritized improvement backlog, concrete examples, a measurement plan and engineering tickets where useful.</dd>
          </div>
          <div>
            <dt>Timing and delivery</dt>
            <dd>Assessment and first recommendations are normally developed over the first few weeks. Your team owns production implementation; we can stay involved through delivery.</dd>
          </div>
        </dl>
      </section>
      <section className="fs-section" aria-label="Our approach">
        <div className="fs-detail-list">
          <section className="fs-detail-row">
            <div className="fs-approach-heading">
              <ApproachIllustration kind="read" />
              <h2>
                Read the search
                <br />
                behind the numbers.
              </h2>
            </div>
            <div>
              <p>
                A headline conversion rate cannot tell you which queries work or
                why others fail. We start with your search data and, where
                possible, access to your search platform.
              </p>
              <p>
                We group queries by intent and category, examine what customers
                see and do next, and review the catalogue, configuration and
                interface together.
              </p>
              <div className="fs-deliverable">
                <strong>What this gives you</strong>A shared picture of your
                search capability, the recurring problems and the gaps in
                measurement.
              </div>
            </div>
          </section>
          <section className="fs-detail-row">
            <div className="fs-approach-heading">
              <ApproachIllustration kind="prioritize" />
              <h2>
                Find the changes
                <br />
                worth making first.
              </h2>
            </div>
            <div>
              <p>
                Some problems appear in thousands of searches. Others matter to
                a particular category, language or customer need. We separate
                them so the loudest example does not automatically become the
                highest priority.
              </p>
              <p>
                The first few weeks focus on practical improvements to the
                search you already run. Each recommendation explains the
                expected benefit, the effort involved and what evidence would
                show it worked.
              </p>
              <div className="fs-deliverable">
                <strong>What this gives you</strong>A prioritized backlog with
                concrete examples, configuration recommendations and engineering
                tickets where needed.
              </div>
            </div>
          </section>
          <section className="fs-detail-row">
            <div className="fs-approach-heading">
              <ApproachIllustration kind="handoff" />
              <h2>
                Make the handoff
                <br />
                useful to engineering.
              </h2>
            </div>
            <div>
              <p>
                “Improve relevance” is not an actionable ticket. Your team needs
                the affected query classes, the current behaviour, the intended
                result and acceptance criteria.
              </p>
              <p>
                We can advise, write those tickets and work closely with your
                product and engineering teams through delivery. Your engineers
                own production implementation; our involvement is agreed around
                the work you need.
              </p>
              <div className="fs-deliverable">
                <strong>What this gives you</strong>Clear decisions your team
                can implement, with a way to verify the result.
              </div>
            </div>
          </section>
          <section className="fs-detail-row">
            <div className="fs-approach-heading">
              <ApproachIllustration kind="measure" />
              <h2>
                Check the result.
                <br />
                Choose the next move.
              </h2>
            </div>
            <div>
              <p>
                We define the baseline and the right measures for the change.
                A/B tests can tell us whether an improvement holds up in real
                use; query evaluation can reveal which kinds of searches still
                need attention.
              </p>
              <p>
                Monthly work builds on those findings: refine ranking, improve
                analytics and search UX, address differences between markets,
                and explore capabilities your platform is not yet using.
              </p>
              <div className="fs-deliverable">
                <strong>What this gives you</strong>A continuing cycle of
                specific improvements, evaluation and informed priorities.
              </div>
            </div>
          </section>
        </div>
      </section>
      <section className="fs-section fs-note-section fs-intro">
        <h2>
          The right depth
          <br />
          for your team.
        </h2>
        <div className="fs-prose">
          <p>
            Some teams need a focused assessment and a clear backlog. Others
            want a specialist alongside them month after month. We agree the
            scope, access and level of involvement before we begin.
          </p>
          <p>
            Early recommendations can take weeks. Implementation and measured
            outcomes depend on the changes, your delivery capacity and the
            traffic needed to evaluate them.
          </p>
        </div>
      </section>
      <ContactBand />
    </>
  );
}
