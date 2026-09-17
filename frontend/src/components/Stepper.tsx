export type StepState = "done" | "current" | "todo";

interface StepperProps {
  steps: Array<{ label: string; hint: string; state: StepState }>;
}

export function Stepper({ steps }: StepperProps) {
  return (
    <ol className="stepper" aria-label="Étapes du parcours">
      {steps.map((step, index) => (
        <li className={`step ${step.state}`} key={step.label} aria-current={step.state === "current" ? "step" : undefined}>
          <span className="step-index" aria-hidden="true">{step.state === "done" ? "✓" : index + 1}</span>
          <span className="step-copy">
            <strong>{step.label}</strong>
            <small>{step.hint}</small>
          </span>
        </li>
      ))}
    </ol>
  );
}
