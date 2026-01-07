import React, { useState, useCallback } from 'react';
import { Upload, X, FileText, Image, File, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Badge } from './ui/badge';

interface UploadedFile {
  id: string;
  file: File;
  preview?: string;
  path?: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

interface DivorceEvidenceUploaderProps {
  onFilesUploaded: (filePaths: string[]) => void;
  maxFiles?: number;
  acceptedTypes?: string[];
}

const EVIDENCE_TYPES = [
  { value: 'credit_card', label: '신용카드 명세서', icon: FileText },
  { value: 'bank_statement', label: '통장 거래내역', icon: FileText },
  { value: 'kakao_chat', label: '카카오톡 대화', icon: Image },
  { value: 'sms', label: '문자 메시지', icon: Image },
  { value: 'photo', label: '사진', icon: Image },
  { value: 'document', label: '기타 문서', icon: File },
];

export const DivorceEvidenceUploader: React.FC<DivorceEvidenceUploaderProps> = ({
  onFilesUploaded,
  maxFiles = 10,
  acceptedTypes = ['image/*', '.pdf', '.jpg', '.jpeg', '.png', '.webp'],
}) => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedEvidenceType, setSelectedEvidenceType] = useState<string>('');

  const uploadFile = useCallback(async (uploadedFile: UploadedFile) => {
    const startTime = performance.now();
    console.log('=' .repeat(80));
    console.log('📤 [파일 업로드] 시작');
    console.log(`📄 파일명: ${uploadedFile.file.name}`);
    console.log(`📦 파일 크기: ${(uploadedFile.file.size / 1024).toFixed(2)} KB`);
    console.log(`📋 파일 타입: ${uploadedFile.file.type}`);

    const formData = new FormData();
    formData.append('file', uploadedFile.file);

    try {
      setFiles(prev =>
        prev.map(f =>
          f.id === uploadedFile.id ? { ...f, status: 'uploading' } : f
        )
      );

      console.log('⬆️ 서버로 업로드 중...');
      const response = await fetch('/api/chat/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const data = await response.json();
      const uploadTime = ((performance.now() - startTime) / 1000).toFixed(2);

      console.log(`✅ 업로드 완료!`);
      console.log(`📁 서버 경로: ${data.file_path}`);
      console.log(`⏱️ 소요시간: ${uploadTime}초`);
      console.log('=' .repeat(80));

      setFiles(prev =>
        prev.map(f =>
          f.id === uploadedFile.id
            ? { ...f, status: 'success', path: data.file_path }
            : f
        )
      );

      return data.file_path;
    } catch (error) {
      const uploadTime = ((performance.now() - startTime) / 1000).toFixed(2);
      console.error('=' .repeat(80));
      console.error('❌ [파일 업로드] 오류 발생!');
      console.error(`📄 파일명: ${uploadedFile.file.name}`);
      console.error(`🚨 오류 메시지: ${error}`);
      console.error(`⏱️ 실패까지 소요시간: ${uploadTime}초`);
      console.error('=' .repeat(80));

      setFiles(prev =>
        prev.map(f =>
          f.id === uploadedFile.id
            ? { ...f, status: 'error', error: String(error) }
            : f
        )
      );
      throw error;
    }
  }, []);

  const handleFiles = useCallback(
    async (newFiles: FileList | File[]) => {
      const fileArray = Array.from(newFiles);

      console.log('=' .repeat(80));
      console.log('📂 [파일 선택] 새 파일 추가');
      console.log(`📦 선택한 파일: ${fileArray.length}개`);
      console.log(`📊 현재 파일: ${files.length}개`);
      console.log(`🎯 최대 허용: ${maxFiles}개`);

      if (files.length + fileArray.length > maxFiles) {
        console.warn(`⚠️ 파일 개수 초과! (${files.length + fileArray.length}/${maxFiles})`);
        alert(`최대 ${maxFiles}개 파일까지 업로드 가능합니다.`);
        return;
      }

      const uploadedFiles: UploadedFile[] = fileArray.map(file => ({
        id: `${Date.now()}-${Math.random()}`,
        file,
        preview: file.type.startsWith('image/')
          ? URL.createObjectURL(file)
          : undefined,
        status: 'pending',
      }));

      console.log('파일 목록:');
      uploadedFiles.forEach((uf, idx) => {
        console.log(`  ${idx + 1}. ${uf.file.name} (${(uf.file.size / 1024).toFixed(2)} KB)`);
      });

      setFiles(prev => [...prev, ...uploadedFiles]);

      // 업로드 시작
      console.log('🚀 병렬 업로드 시작...');
      const uploadPromises = uploadedFiles.map(f => uploadFile(f));
      const paths = await Promise.all(uploadPromises);
      const successPaths = paths.filter(p => p !== undefined) as string[];

      console.log(`✅ 업로드 결과: ${successPaths.length}/${uploadedFiles.length} 성공`);
      console.log('=' .repeat(80));

      if (successPaths.length > 0) {
        onFilesUploaded(successPaths);
      }
    },
    [files.length, maxFiles, uploadFile, onFilesUploaded]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      if (e.dataTransfer.files) {
        handleFiles(e.dataTransfer.files);
      }
    },
    [handleFiles]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const removeFile = useCallback((id: string) => {
    setFiles(prev => {
      const file = prev.find(f => f.id === id);
      if (file?.preview) {
        URL.revokeObjectURL(file.preview);
      }
      return prev.filter(f => f.id !== id);
    });
  }, []);

  const getFileIcon = (file: UploadedFile) => {
    if (file.file.type.startsWith('image/')) return Image;
    if (file.file.type === 'application/pdf') return FileText;
    return File;
  };

  const getStatusIcon = (status: UploadedFile['status']) => {
    switch (status) {
      case 'success':
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-4">
      {/* 증거 유형 선택 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          증거 유형
        </label>
        <div className="flex flex-wrap gap-2">
          {EVIDENCE_TYPES.map(type => {
            const Icon = type.icon;
            return (
              <Button
                key={type.value}
                variant={selectedEvidenceType === type.value ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedEvidenceType(type.value)}
                className="text-xs"
              >
                <Icon className="w-3 h-3 mr-1" />
                {type.label}
              </Button>
            );
          })}
        </div>
      </div>

      {/* 파일 업로드 영역 */}
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <Upload className="w-12 h-12 mx-auto text-gray-400 mb-4" />
        <p className="text-sm text-gray-600 mb-2">
          파일을 드래그 앤 드롭하거나 클릭하여 업로드하세요
        </p>
        <p className="text-xs text-gray-500 mb-4">
          이미지 (JPG, PNG, WEBP), PDF (최대 {maxFiles}개)
        </p>
        <input
          type="file"
          multiple
          accept={acceptedTypes.join(',')}
          onChange={e => e.target.files && handleFiles(e.target.files)}
          className="hidden"
          id="file-upload"
        />
        <label htmlFor="file-upload">
          <Button variant="outline" className="cursor-pointer" asChild>
            <span>파일 선택</span>
          </Button>
        </label>
      </div>

      {/* 업로드된 파일 목록 */}
      {files.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-gray-700">
            업로드된 파일 ({files.length})
          </h3>
          <div className="grid grid-cols-1 gap-2">
            {files.map(file => {
              const Icon = getFileIcon(file);
              return (
                <Card key={file.id} className="p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3 flex-1 min-w-0">
                      {file.preview ? (
                        <img
                          src={file.preview}
                          alt={file.file.name}
                          className="w-12 h-12 object-cover rounded"
                        />
                      ) : (
                        <div className="w-12 h-12 bg-gray-100 rounded flex items-center justify-center">
                          <Icon className="w-6 h-6 text-gray-400" />
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {file.file.name}
                        </p>
                        <p className="text-xs text-gray-500">
                          {(file.file.size / 1024).toFixed(1)} KB
                        </p>
                        {file.error && (
                          <p className="text-xs text-red-500 mt-1">{file.error}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(file.status)}
                      <Badge
                        variant={
                          file.status === 'success'
                            ? 'default'
                            : file.status === 'error'
                            ? 'destructive'
                            : 'outline'
                        }
                        className="text-xs"
                      >
                        {file.status === 'uploading'
                          ? '업로드 중...'
                          : file.status === 'success'
                          ? '완료'
                          : file.status === 'error'
                          ? '실패'
                          : '대기 중'}
                      </Badge>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFile(file.id)}
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* 안내 메시지 */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex">
          <AlertCircle className="w-5 h-5 text-yellow-600 mr-2 flex-shrink-0" />
          <div className="text-sm text-yellow-800">
            <p className="font-medium mb-1">⚠️ 증거 수집 주의사항</p>
            <ul className="list-disc list-inside space-y-1 text-xs">
              <li>합법적으로 취득한 증거만 업로드하세요</li>
              <li>타인 몰래 촬영하거나 도청한 자료는 불법입니다</li>
              <li>개인정보는 자동으로 마스킹 처리됩니다</li>
              <li>AI 분석은 참고용이며 법적 효력이 없습니다</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
