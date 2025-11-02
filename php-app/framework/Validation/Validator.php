<?php

declare(strict_types=1);

namespace Framework\Validation;

final class Validator
{
    /** @param array<string, mixed> $data */
    public function __construct(private array $data)
    {
    }

    /** @param array<string, string> $rules */
    public function validate(array $rules): array
    {
        $errors = [];

        foreach ($rules as $field => $rule) {
            $value = $this->data[$field] ?? null;
            foreach (explode('|', $rule) as $constraint) {
                if ($constraint === 'required' && ($value === null || $value === '')) {
                    $errors[$field][] = 'validation.required';
                }

                if ($constraint === 'email' && $value !== null && $value !== '' && !filter_var($value, FILTER_VALIDATE_EMAIL)) {
                    $errors[$field][] = 'validation.email';
                }

                if (str_starts_with($constraint, 'min:')) {
                    $min = (int) substr($constraint, 4);
                    if (is_string($value) && mb_strlen($value) < $min) {
                        $errors[$field][] = 'validation.min';
                    }
                }
            }
        }

        return $errors;
    }
}
