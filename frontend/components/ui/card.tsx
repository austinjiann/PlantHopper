"use client";

import * as React from "react";

type DivProps = React.HTMLAttributes<HTMLDivElement>;

export function Card({ className, ...props }: DivProps) {
  return <div className={`card ${className ?? ""}`} {...props} />;
}

export function CardHeader({ className, ...props }: DivProps) {
  return <div className={className} {...props} />;
}

export function CardTitle({ className, ...props }: DivProps) {
  return <h3 className={className} {...props} />;
}

export function CardDescription({ className, ...props }: DivProps) {
  return <p className={`secondary-text ${className ?? ""}`} {...props} />;
}

export function CardContent({ className, ...props }: DivProps) {
  return <div className={className} {...props} />;
}

export function CardFooter({ className, ...props }: DivProps) {
  return <div className={className} {...props} />;
}


