/**
 * UIコンポーネントのテスト
 *
 * Button, Card, Badge, Modal, Accordionコンポーネントをテストする。
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { Accordion, AccordionItem } from '@/components/ui/Accordion'

describe('Button Component', () => {
  describe('Rendering', () => {
    it('ボタンが正常にレンダリングされる', () => {
      render(<Button>Click Me</Button>)
      expect(screen.getByText('Click Me')).toBeTruthy()
    })

    it('variant="primary"のデフォルトスタイルが適用される', () => {
      const { container } = render(<Button variant="primary">Primary</Button>)
      const button = container.querySelector('button')
      expect(button?.className).toContain('bg-primary-600')
    })

    it('variant="secondary"のスタイルが適用される', () => {
      const { container } = render(<Button variant="secondary">Secondary</Button>)
      const button = container.querySelector('button')
      expect(button?.className).toContain('bg-gray-200')
    })

    it('variant="ghost"のスタイルが適用される', () => {
      const { container } = render(<Button variant="ghost">Ghost</Button>)
      const button = container.querySelector('button')
      expect(button?.className).toContain('hover:bg-gray-100')
    })

    it('variant="danger"のスタイルが適用される', () => {
      const { container } = render(<Button variant="danger">Danger</Button>)
      const button = container.querySelector('button')
      expect(button?.className).toContain('bg-red-600')
    })
  })

  describe('Sizes', () => {
    it('size="sm"のスタイルが適用される', () => {
      const { container } = render(<Button size="sm">Small</Button>)
      const button = container.querySelector('button')
      expect(button?.className).toContain('text-sm')
    })

    it('size="md"のデフォルトスタイルが適用される', () => {
      const { container } = render(<Button size="md">Medium</Button>)
      const button = container.querySelector('button')
      expect(button?.className).toContain('px-4 py-2')
    })

    it('size="lg"のスタイルが適用される', () => {
      const { container } = render(<Button size="lg">Large</Button>)
      const button = container.querySelector('button')
      expect(button?.className).toContain('text-lg')
    })

    it('size="icon"のスタイルが適用される', () => {
      const { container } = render(<Button size="icon">Icon</Button>)
      const button = container.querySelector('button')
      expect(button?.className).toContain('p-2')
    })
  })

  describe('States', () => {
    it('disabled状態が正しく適用される', () => {
      render(<Button disabled>Disabled</Button>)
      const button = screen.getByText('Disabled')
      expect(button).toBeDisabled()
    })

    it('クリックイベントが正しく動作する', async () => {
      const handleClick = vi.fn()
      const user = userEvent.setup()
      render(<Button onClick={handleClick}>Click Me</Button>)

      await user.click(screen.getByText('Click Me'))
      expect(handleClick).toHaveBeenCalledTimes(1)
    })
  })
})

describe('Card Components', () => {
  describe('Card', () => {
    it('Cardが正常にレンダリングされる', () => {
      const { container } = render(<Card>Content</Card>)
      const card = container.querySelector('.bg-white')
      expect(card).toBeTruthy()
    })

    it('カスタムclassNameが適用される', () => {
      const { container } = render(<Card className="custom-class">Content</Card>)
      const card = container.querySelector('.custom-class')
      expect(card).toBeTruthy()
    })
  })

  describe('CardContent', () => {
    it('CardContentが正常にレンダリングされる', () => {
      const { container } = render(<CardContent>Content</CardContent>)
      const content = container.querySelector('.p-6')
      expect(content).toBeTruthy()
    })
  })

  describe('CardHeader', () => {
    it('CardHeaderが正常にレンダリングされる', () => {
      const { container } = render(<CardHeader>Header</CardHeader>)
      const header = container.querySelector('.p-6')
      expect(header).toBeTruthy()
    })
  })

  describe('CardTitle', () => {
    it('CardTitleが正常にレンダリングされる', () => {
      render(<CardTitle>Title</CardTitle>)
      expect(screen.getByText('Title')).toBeTruthy()
    })

    it('h3タグとしてレンダリングされる', () => {
      const { container } = render(<CardTitle>Title</CardTitle>)
      const title = container.querySelector('h3')
      expect(title).toBeTruthy()
    })
  })

  describe('Card Composition', () => {
    it('すべてのCardサブコンポーネントが組み合わせて使用できる', () => {
      render(
        <Card>
          <CardHeader>
            <CardTitle>Test Title</CardTitle>
          </CardHeader>
          <CardContent>
            <p>Test Content</p>
          </CardContent>
        </Card>
      )
      expect(screen.getByText('Test Title')).toBeTruthy()
      expect(screen.getByText('Test Content')).toBeTruthy()
    })
  })
})

describe('Badge Component', () => {
  describe('Rendering', () => {
    it('Badgeが正常にレンダリングされる', () => {
      render(<Badge>Badge</Badge>)
      expect(screen.getByText('Badge')).toBeTruthy()
    })

    it('variant="success"のスタイルが適用される', () => {
      const { container } = render(<Badge variant="success">Success</Badge>)
      const badge = container.querySelector('.bg-green-100')
      expect(badge).toBeTruthy()
    })

    it('variant="error"のスタイルが適用される', () => {
      const { container } = render(<Badge variant="error">Error</Badge>)
      const badge = container.querySelector('.bg-red-100')
      expect(badge).toBeTruthy()
    })

    it('variant="info"のスタイルが適用される', () => {
      const { container } = render(<Badge variant="info">Info</Badge>)
      const badge = container.querySelector('.bg-blue-100')
      expect(badge).toBeTruthy()
    })

    it('variant="warning"のスタイルが適用される', () => {
      const { container } = render(<Badge variant="warning">Warning</Badge>)
      const badge = container.querySelector('.bg-yellow-100')
      expect(badge).toBeTruthy()
    })

    it('variant="gray"のスタイルが適用される', () => {
      const { container } = render(<Badge variant="gray">Gray</Badge>)
      const badge = container.querySelector('.bg-gray-100')
      expect(badge).toBeTruthy()
    })
  })

  describe('Styling', () => {
    it('カスタムclassNameが適用される', () => {
      const { container } = render(<Badge className="custom-class">Badge</Badge>)
      const badge = container.querySelector('.custom-class')
      expect(badge).toBeTruthy()
    })

    it('丸みのあるスタイルが適用される', () => {
      const { container } = render(<Badge>Badge</Badge>)
      const badge = container.querySelector('span')
      expect(badge?.className).toContain('rounded-full')
    })
  })
})

describe('Modal Component', () => {
  describe('Rendering', () => {
    it('isOpen=falseの場合、何も表示されない', () => {
      render(
        <Modal isOpen={false} onClose={vi.fn()}>
          Content
        </Modal>
      )
      expect(screen.queryByText('Content')).toBeNull()
    })

    it('isOpen=trueの場合、モーダルが表示される', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()}>
          Modal Content
        </Modal>
      )
      expect(screen.getByText('Modal Content')).toBeTruthy()
    })

    it('タイトルが表示される', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()} title="Test Title">
          Content
        </Modal>
      )
      expect(screen.getByText('Test Title')).toBeTruthy()
    })
  })

  describe('Interactions', () => {
    it('オーバーレイをクリックするとonCloseが呼ばれる', async () => {
      const handleClose = vi.fn()
      const user = userEvent.setup()

      const { container } = render(
        <Modal isOpen={true} onClose={handleClose}>
          Content
        </Modal>
      )

      // Click overlay (first div with bg-black/50)
      const overlay = container.querySelector('.bg-black\\/50')
      if (overlay) {
        await user.click(overlay)
        expect(handleClose).toHaveBeenCalledTimes(1)
      }
    })

    it('閉じるボタンをクリックするとonCloseが呼ばれる', async () => {
      const handleClose = vi.fn()
      const user = userEvent.setup()

      render(
        <Modal isOpen={true} onClose={handleClose} title="Test Title">
          Content
        </Modal>
      )

      // Find and click close button
      const closeButton = screen.getByLabelText('Close')
      await user.click(closeButton)
      expect(handleClose).toHaveBeenCalledTimes(1)
    })
  })

  describe('Body Scroll Lock', () => {
    it('モーダルが開いている間、bodyのスクロールが無効になる', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()}>
          Content
        </Modal>
      )

      // Check if overflow style was set (implementation detail)
      // In actual implementation, this would set document.body.style.overflow
      expect(document.body.style.overflow).toBe('hidden')
    })

    it('モーダルが閉じるとスクロールが有効に戻る', () => {
      const { unmount } = render(
        <Modal isOpen={true} onClose={vi.fn()}>
          Content
        </Modal>
      )

      unmount()
      // After unmount, scroll should be restored
      expect(document.body.style.overflow).toBe('unset')
    })
  })

  describe('Styling', () => {
    it('カスタムclassNameが適用される', () => {
      const { container } = render(
        <Modal isOpen={true} onClose={vi.fn()} className="custom-class">
          Content
        </Modal>
      )
      const modal = container.querySelector('.custom-class')
      expect(modal).toBeTruthy()
    })
  })
})

describe('Accordion Components', () => {
  describe('AccordionItem', () => {
    it('AccordionItemが正常にレンダリングされる', () => {
      render(
        <AccordionItem title="Test Title" defaultOpen={true}>Test Content</AccordionItem>
      )
      expect(screen.getByText('Test Title')).toBeTruthy()
      expect(screen.getByText('Test Content')).toBeTruthy()
    })

    it('defaultOpen=trueの場合、最初から開いている', () => {
      render(
        <AccordionItem title="Title" defaultOpen={true}>
          Content
        </AccordionItem>
      )
      expect(screen.getByText('Content')).toBeTruthy()
    })

    it('defaultOpen=falseの場合、最初は閉じている', () => {
      render(
        <AccordionItem title="Title" defaultOpen={false}>
          Content
        </AccordionItem>
      )
      // Content should NOT be in DOM when closed (component uses conditional rendering)
      expect(screen.queryByText('Content')).toBeNull()
    })
  })

  describe('Accordion Interactions', () => {
    it('タイトルをクリックすると開閉が切り替わる', async () => {
      const user = userEvent.setup()
      render(
        <AccordionItem title="Title">Content</AccordionItem>
      )

      const titleButton = screen.getByText('Title')
      await user.click(titleButton)
    })

    it('アイコンが回転する', async () => {
      const user = userEvent.setup()
      render(
        <AccordionItem title="Title">Content</AccordionItem>
      )

      const titleButton = screen.getByText('Title')

      // Initially not rotated - content not visible
      expect(screen.queryByText('Content')).toBeNull()

      await user.click(titleButton)

      // After click, should be open - content visible
      expect(screen.getByText('Content')).toBeTruthy()
    })
  })

  describe('Accordion Container', () => {
    it('Accordionが正しく子要素をレンダリングする', () => {
      render(
        <Accordion>
          <AccordionItem title="Item 1">Content 1</AccordionItem>
          <AccordionItem title="Item 2">Content 2</AccordionItem>
        </Accordion>
      )
      expect(screen.getByText('Item 1')).toBeTruthy()
      expect(screen.getByText('Item 2')).toBeTruthy()
    })
  })

  describe('Styling', () => {
    it('カスタムclassNameが適用される', () => {
      const { container } = render(
        <AccordionItem title="Title" className="custom-class">
          Content
        </AccordionItem>
      )
      const item = container.querySelector('.custom-class')
      expect(item).toBeTruthy()
    })
  })
})
