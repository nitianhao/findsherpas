import Link from "next/link";
import { ArrowDown, ArrowUpRight } from "lucide-react";
import { BackToTop } from "@/components/site/back-to-top";
import { ContactBand } from "@/components/site/contact-band";

export type FrameworkStage = {
  id: string;
  title: string;
  summary: string;
  detail: string;
  example: {
    query: string;
    weak: string;
    useful: string;
  };
  questions: string[];
  evidence: string[];
  actions: string[];
  decisionRule: string;
};

type FrameworkArticleProps = {
  title: string;
  introduction: string;
  principle: string;
  scope: string;
  flow: string[];
  stages: FrameworkStage[];
  methodTitle: string;
  methodIntroduction: string;
  method: Array<{ title: string; description: string; output: string }>;
  worksheetRows: Array<{ field: string; capture: string; reason: string }>;
  related: {
    href: string;
    title: string;
    description: string;
  };
};

export function FrameworkArticle({
  title,
  introduction,
  principle,
  scope,
  flow,
  stages,
  methodTitle,
  methodIntroduction,
  method,
  worksheetRows,
  related,
}: FrameworkArticleProps) {
  return (
    <>
      <article className="fs-framework">
        <section className="fs-framework-hero" id="overview">
          <h1>{title}</h1>
          <div className="fs-framework-hero-copy">
            <p className="fs-framework-lede">{introduction}</p>
            <p className="fs-framework-scope">{scope}</p>
          </div>
        </section>

        <section className="fs-framework-principle" aria-label="Core principle">
          <p>{principle}</p>
          <div className="fs-framework-flow" aria-label="Framework sequence">
            {flow.map((step, index) => (
              <div className="fs-framework-flow-step" key={step}>
                <span>{step}</span>
                {index < flow.length - 1 ? (
                  <ArrowDown size={19} aria-hidden="true" />
                ) : null}
              </div>
            ))}
          </div>
        </section>

        <nav className="fs-framework-index" aria-label="On this page">
          <p>Use the framework</p>
          <ol>
            {stages.map((stage, index) => (
              <li key={stage.id}>
                <a href={`#${stage.id}`}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  {stage.title}
                </a>
              </li>
            ))}
          </ol>
        </nav>

        <div className="fs-framework-stages">
          {stages.map((stage, index) => (
            <section className="fs-framework-stage" id={stage.id} key={stage.id}>
              <header>
                <span aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <h2>{stage.title}</h2>
                  <p>{stage.summary}</p>
                </div>
              </header>

              <div className="fs-framework-stage-body">
                <p className="fs-framework-detail">{stage.detail}</p>

                <figure className="fs-framework-example">
                  <figcaption>Illustrative diagnosis</figcaption>
                  <p className="fs-framework-query">{stage.example.query}</p>
                  <div>
                    <p>
                      <span>Weak reading</span>
                      {stage.example.weak}
                    </p>
                    <p>
                      <span>Useful reading</span>
                      {stage.example.useful}
                    </p>
                  </div>
                </figure>

                <div className="fs-framework-diagnostic-grid">
                  <section>
                    <h3>Questions to ask</h3>
                    <ul>
                      {stage.questions.map((question) => (
                        <li key={question}>{question}</li>
                      ))}
                    </ul>
                  </section>
                  <section>
                    <h3>Evidence to inspect</h3>
                    <ul>
                      {stage.evidence.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </section>
                  <section>
                    <h3>What to try</h3>
                    <ul>
                      {stage.actions.map((action) => (
                        <li key={action}>{action}</li>
                      ))}
                    </ul>
                  </section>
                  <aside>
                    <h3>Decision rule</h3>
                    <p>{stage.decisionRule}</p>
                  </aside>
                </div>
              </div>
            </section>
          ))}
        </div>

        <section className="fs-framework-method" id="working-method">
          <div>
            <h2>{methodTitle}</h2>
            <p>{methodIntroduction}</p>
          </div>
          <ol>
            {method.map((step, index) => (
              <li key={step.title}>
                <span>{index + 1}</span>
                <div>
                  <h3>{step.title}</h3>
                  <p>{step.description}</p>
                  <p className="fs-framework-output">
                    <strong>Output:</strong> {step.output}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section className="fs-framework-worksheet" id="worksheet">
          <div className="fs-section-heading">
            <h2>A small worksheet is enough to begin.</h2>
            <p>
              Capture one row per query. The discipline is separating what the
              customer asked for, what the system did, and what evidence would
              justify a change.
            </p>
          </div>
          <div className="fs-framework-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Field</th>
                  <th>What to capture</th>
                  <th>Why it matters</th>
                </tr>
              </thead>
              <tbody>
                {worksheetRows.map((row) => (
                  <tr key={row.field}>
                    <th scope="row">{row.field}</th>
                    <td>{row.capture}</td>
                    <td>{row.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="fs-framework-next" aria-labelledby="framework-next-title">
          <h2 id="framework-next-title">Continue the diagnosis.</h2>
          <div>
            <Link href="/search-check">
              <span>Run a quick check</span>
              Test six query patterns on your own store.
              <ArrowUpRight aria-hidden="true" />
            </Link>
            <Link href={related.href}>
              <span>{related.title}</span>
              {related.description}
              <ArrowUpRight aria-hidden="true" />
            </Link>
          </div>
        </section>
      </article>
      <ContactBand />
      <BackToTop />
    </>
  );
}
