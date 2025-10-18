import { useState, useCallback } from 'react'
import Cropper, { type Area } from 'react-easy-crop'

interface ImageCropperProps {
  image: string
  onCropComplete: (croppedBlob: Blob) => void
  onCancel: () => void
}

/**
 * 创建图片并返回 Image 对象
 */
const createImage = (url: string): Promise<HTMLImageElement> =>
  new Promise((resolve, reject) => {
    const image = new Image()
    image.addEventListener('load', () => resolve(image))
    image.addEventListener('error', (error) => reject(error))
    image.src = url
  })

/**
 * 根据裁剪区域获取裁剪后的图片
 */
async function getCroppedImg(
  imageSrc: string,
  pixelCrop: Area
): Promise<Blob> {
  const image = await createImage(imageSrc)
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')

  if (!ctx) {
    throw new Error('无法获取canvas context')
  }

  // 设置canvas尺寸为裁剪区域尺寸
  canvas.width = pixelCrop.width
  canvas.height = pixelCrop.height

  // 绘制裁剪后的图片
  ctx.drawImage(
    image,
    pixelCrop.x,
    pixelCrop.y,
    pixelCrop.width,
    pixelCrop.height,
    0,
    0,
    pixelCrop.width,
    pixelCrop.height
  )

  // 转换为blob
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) {
        resolve(blob)
      } else {
        reject(new Error('Canvas转换为Blob失败'))
      }
    }, 'image/jpeg', 0.95)
  })
}

export function ImageCropper({ image, onCropComplete, onCancel }: ImageCropperProps) {
  const [crop, setCrop] = useState({ x: 0, y: 0 })
  const [zoom, setZoom] = useState(1)
  const [croppedAreaPixels, setCroppedAreaPixels] = useState<Area | null>(null)
  const [processing, setProcessing] = useState(false)

  const onCropChange = (location: { x: number; y: number }) => {
    setCrop(location)
  }

  const onCropCompleteInternal = useCallback(
    (_croppedArea: Area, croppedAreaPixels: Area) => {
      setCroppedAreaPixels(croppedAreaPixels)
    },
    []
  )

  const handleConfirm = async () => {
    if (!croppedAreaPixels) return

    setProcessing(true)
    try {
      const croppedBlob = await getCroppedImg(image, croppedAreaPixels)
      onCropComplete(croppedBlob)
    } catch (e) {
      console.error('裁剪失败:', e)
      alert('裁剪失败，请重试')
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.9)',
        zIndex: 10000,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* 裁剪区域 */}
      <div style={{ position: 'relative', flex: 1, minHeight: 0 }}>
        <Cropper
          image={image}
          crop={crop}
          zoom={zoom}
          aspect={1}
          cropShape="rect"
          showGrid={true}
          onCropChange={onCropChange}
          onCropComplete={onCropCompleteInternal}
          onZoomChange={setZoom}
        />
      </div>

      {/* 控制面板 */}
      <div
        style={{
          backgroundColor: '#1f2937',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        {/* 缩放滑块 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: '#fff' }}>
          <span style={{ fontSize: '14px', minWidth: '60px' }}>缩放</span>
          <input
            type="range"
            min={1}
            max={3}
            step={0.1}
            value={zoom}
            onChange={(e) => setZoom(Number(e.target.value))}
            style={{ flex: 1 }}
          />
          <span style={{ fontSize: '14px', minWidth: '40px', textAlign: 'right' }}>
            {zoom.toFixed(1)}x
          </span>
        </div>

        {/* 提示文字 */}
        <div style={{ color: '#9ca3af', fontSize: '13px', textAlign: 'center' }}>
          拖动图片调整位置，使用滑块缩放
        </div>

        {/* 按钮 */}
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={onCancel}
            disabled={processing}
            style={{
              flex: 1,
              padding: '12px',
              backgroundColor: '#374151',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              fontSize: '15px',
              cursor: processing ? 'not-allowed' : 'pointer',
              opacity: processing ? 0.5 : 1,
            }}
          >
            取消
          </button>
          <button
            onClick={handleConfirm}
            disabled={processing}
            style={{
              flex: 1,
              padding: '12px',
              background: processing ? '#6b7280' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              fontSize: '15px',
              fontWeight: 600,
              cursor: processing ? 'not-allowed' : 'pointer',
            }}
          >
            {processing ? '处理中...' : '确认裁剪'}
          </button>
        </div>
      </div>
    </div>
  )
}

