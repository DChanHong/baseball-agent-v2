"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";
import styled, { css } from "styled-components";

type ButtonVariant = "primary" | "secondary" | "ghost";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  variant?: ButtonVariant;
};

export function Button({ children, variant = "secondary", ...props }: ButtonProps) {
  return (
    <StyledButton $variant={variant} {...props}>
      {children}
    </StyledButton>
  );
}

const variantStyle = {
  primary: css`
    background: ${({ theme }) => theme.color.primary};
    border-color: ${({ theme }) => theme.color.primary};
    color: #ffffff;

    &:hover {
      background: ${({ theme }) => theme.color.primaryHover};
    }
  `,
  secondary: css`
    background: ${({ theme }) => theme.color.panel};
    border-color: ${({ theme }) => theme.color.border};
    color: ${({ theme }) => theme.color.foreground};
  `,
  ghost: css`
    background: transparent;
    border-color: transparent;
    color: ${({ theme }) => theme.color.muted};
  `,
};

const StyledButton = styled.button<{ $variant: ButtonVariant }>`
  min-height: 40px;
  border: 1px solid;
  border-radius: ${({ theme }) => theme.radius.sm};
  padding: 0 14px;
  font-weight: 700;
  transition:
    background 160ms ease,
    border-color 160ms ease,
    color 160ms ease;

  ${({ $variant }) => variantStyle[$variant]}

  &:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }
`;
