import type { ComponentProps } from "react";

import Link from "next/link";

function H2(props: ComponentProps<"h2">) {
  return (
    <h2
      {...props}
      className={[
        "mt-10 scroll-m-20 text-2xl font-semibold tracking-tight",
        props.className,
      ]
        .filter(Boolean)
        .join(" ")}
    />
  );
}

function H3(props: ComponentProps<"h3">) {
  return (
    <h3
      {...props}
      className={[
        "mt-8 scroll-m-20 text-xl font-semibold tracking-tight",
        props.className,
      ]
        .filter(Boolean)
        .join(" ")}
    />
  );
}

function P(props: ComponentProps<"p">) {
  return (
    <p
      {...props}
      className={[
        "mt-4 leading-7 text-muted-foreground",
        props.className,
      ]
        .filter(Boolean)
        .join(" ")}
    />
  );
}

function Ul(props: ComponentProps<"ul">) {
  return (
    <ul
      {...props}
      className={["mt-4 ml-6 list-disc text-muted-foreground", props.className]
        .filter(Boolean)
        .join(" ")}
    />
  );
}

function Ol(props: ComponentProps<"ol">) {
  return (
    <ol
      {...props}
      className={[
        "mt-4 ml-6 list-decimal text-muted-foreground",
        props.className,
      ]
        .filter(Boolean)
        .join(" ")}
    />
  );
}

function Li(props: ComponentProps<"li">) {
  return <li {...props} className={["mt-2", props.className].filter(Boolean).join(" ")} />;
}

function A(props: ComponentProps<"a">) {
  const href = props.href ?? "#";
  if (href.startsWith("/")) {
    return (
      <Link
        href={href}
        className={[
          "underline underline-offset-4 decoration-muted-foreground/40 hover:decoration-muted-foreground",
          props.className,
        ]
          .filter(Boolean)
          .join(" ")}
      >
        {props.children}
      </Link>
    );
  }

  return (
    <a
      {...props}
      className={[
        "underline underline-offset-4 decoration-muted-foreground/40 hover:decoration-muted-foreground",
        props.className,
      ]
        .filter(Boolean)
        .join(" ")}
    />
  );
}

export const mdxComponents = {
  h2: H2,
  h3: H3,
  p: P,
  ul: Ul,
  ol: Ol,
  li: Li,
  a: A,
};

