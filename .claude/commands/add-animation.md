---
name: add-animation
description: Add Framer Motion animations including hover effects, entrance animations, scroll triggers, and exit animations
---

# /add-animation Command

**Purpose**: Add declarative, performant animations to components using Framer Motion. Includes hover/tap effects, entrance/exit animations, and scroll-triggered animations.

## Usage

```bash
/add-animation
```

The command will guide you through animation types and generate the appropriate Framer Motion code.

## Animation Types

### 1. Hover/Tap Effects (Micro-interactions)

```tsx
'use client';

import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';

<motion.div
  whileHover={{ scale: 1.05 }}
  whileTap={{ scale: 0.95 }}
  transition={{ duration: 0.2 }}
>
  <Button>Click Me</Button>
</motion.div>
```

### 2. Entrance Animations (Mount)

```tsx
'use client';

import { motion } from 'framer-motion';

<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.5 }}
>
  Content fades in and slides up
</motion.div>
```

### 3. Exit Animations (Unmount)

**CRITICAL**: Must wrap in `<AnimatePresence>`

```tsx
'use client';

import { motion, AnimatePresence } from 'framer-motion';

<AnimatePresence>
  {isVisible && (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      Content with exit animation
    </motion.div>
  )}
</AnimatePresence>
```

### 4. Scroll-Triggered Animations

```tsx
'use client';

import { motion } from 'framer-motion';

<motion.div
  initial={{ opacity: 0, y: 50 }}
  whileInView={{ opacity: 1, y: 0 }}
  viewport={{ once: true }}  // Only animate once
  transition={{ duration: 0.6 }}
>
  Appears when scrolled into view
</motion.div>
```

## Common Animation Patterns

### Card Hover Effect

```tsx
'use client';

import { motion } from 'framer-motion';
import { Card } from '@/components/ui/card';

export function AnimatedCard({ children }) {
  return (
    <motion.div
      whileHover={{ 
        scale: 1.02,
        boxShadow: "0 20px 25px -5px rgb(0 0 0 / 0.1)",
      }}
      transition={{ duration: 0.2 }}
    >
      <Card>{children}</Card>
    </motion.div>
  );
}
```

### Staggered List Animation

```tsx
'use client';

import { motion } from 'framer-motion';

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
};

const item = {
  hidden: { opacity: 0, x: -20 },
  show: { opacity: 1, x: 0 }
};

export function StaggeredList({ items }) {
  return (
    <motion.ul
      variants={container}
      initial="hidden"
      animate="show"
    >
      {items.map(item => (
        <motion.li key={item.id} variants={item}>
          {item.text}
        </motion.li>
      ))}
    </motion.ul>
  );
}
```

### Button with Loading Spinner

```tsx
'use client';

import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';

<Button disabled={isLoading}>
  {isLoading ? (
    <motion.div
      animate={{ rotate: 360 }}
      transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
    >
      <Loader2 size={16} />
    </motion.div>
  ) : (
    "Submit"
  )}
</Button>
```

### Modal/Dialog with Backdrop

```tsx
'use client';

import { motion, AnimatePresence } from 'framer-motion';

<AnimatePresence>
  {isOpen && (
    <>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 z-50"
        onClick={onClose}
      />
      
      {/* Modal */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        transition={{ duration: 0.2 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <Card className="w-full max-w-md">
          {/* Dialog content */}
        </Card>
      </motion.div>
    </>
  )}
</AnimatePresence>
```

## Transition Options

```tsx
// Spring (physics-based, natural feel)
transition={{ type: "spring", stiffness: 300, damping: 30 }}

// Tween (duration-based, predictable)
transition={{ duration: 0.3, ease: "easeInOut" }}

// Custom easing
transition={{ duration: 0.5, ease: [0.43, 0.13, 0.23, 0.96] }}
```

## Performance Best Practices

✅ **Do**:
- Animate `transform` properties (x, y, scale, rotate)
- Animate `opacity`
- Use `whileInView` with `viewport={{ once: true }}`
- Keep animations under 500ms for UI interactions
- Use `AnimatePresence` for exit animations

❌ **Don't**:
- Animate layout properties (width, height, margin, padding)
- Animate without `'use client'` directive
- Forget `AnimatePresence` for exit animations
- Create complex animations on every scroll event
- Animate too many elements simultaneously

## Troubleshooting

**Issue**: "Animation doesn't exit smoothly"
**Solution**: Wrap in `<AnimatePresence>` and add `exit` prop

**Issue**: "Hydration mismatch error"
**Solution**: Ensure component has `'use client'` directive

**Issue**: "Animation is janky/laggy"
**Solution**: Only animate transform and opacity, avoid layout properties

---

**Related Commands**: `/add-component`, `/style-responsive`
**Skill Dependencies**: `framer-motion-interactive-animation`
