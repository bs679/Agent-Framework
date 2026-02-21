import React from 'react';
import { createRoot } from 'react-dom/client';
import { OnboardingForm } from './components/OnboardingForm.jsx';

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <OnboardingForm />
  </React.StrictMode>
);
