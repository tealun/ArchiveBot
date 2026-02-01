"""
Export manager module
Exports archives, tags, and notes to various formats
"""

import logging
import json
import csv
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from io import StringIO

from ..utils.helpers import format_datetime

logger = logging.getLogger(__name__)


class ExportManager:
    """
    Manages data export functionality
    Supports Markdown, JSON, and CSV formats
    """
    
    def __init__(self, db, note_manager, tag_manager=None):
        """
        Initialize export manager
        
        Args:
            db: Database instance
            note_manager: NoteManager instance
            tag_manager: TagManager instance (optional)
        """
        self.db = db
        self.note_manager = note_manager
        self.tag_manager = tag_manager
        logger.info("ExportManager initialized")
    
    def export_to_json(self, include_deleted: bool = False) -> str:
        """
        Export all data to JSON format
        
        Args:
            include_deleted: Include deleted archives
            
        Returns:
            JSON string
        """
        try:
            data = {
                'export_date': format_datetime(),
                'archives': [],
                'tags': {},
                'statistics': {}
            }
            
            # Export archives
            with self.db._lock:
                deleted_filter = "" if include_deleted else "WHERE deleted = 0"
                cursor = self.db.execute(f"""
                    SELECT 
                        id, title, content, content_type,
                        file_size, file_id,
                        storage_type, source, metadata,
                        created_at, deleted, deleted_at
                    FROM archives
                    {deleted_filter}
                    ORDER BY created_at DESC
                """)
                
                for row in cursor.fetchall():
                    archive_id = row[0]
                    
                    # 通过 tag_manager 获取标签
                    tags = self.tag_manager.get_archive_tags(archive_id) if self.tag_manager else []
                    
                    archive = {
                        'id': archive_id,
                        'title': row[1],
                        'content': row[2],
                        'content_type': row[3],
                        'tags': tags,
                        'file_size': row[4],
                        'file_id': row[5],
                        'storage_type': row[6],
                        'source': row[7],
                        'metadata': row[8],
                        'created_at': row[9],
                        'deleted': bool(row[10]),
                        'deleted_at': row[11]
                    }
                    
                    # Add notes
                    notes = self.note_manager.get_notes(archive_id)
                    archive['notes'] = notes
                    
                    data['archives'].append(archive)
                
                # Export tag statistics - 使用tag_manager获取
                if self.tag_manager:
                    all_tags = self.tag_manager.get_all_tags(limit=1000)
                    tag_counts = {tag['tag_name']: tag['count'] for tag in all_tags}
                else:
                    tag_counts = {}
                
                data['tags'] = tag_counts
                
                # Statistics
                cursor = self.db.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN deleted = 0 THEN 1 END) as active,
                        COUNT(CASE WHEN deleted = 1 THEN 1 END) as deleted
                    FROM archives
                """)
                stats = cursor.fetchone()
                data['statistics'] = {
                    'total_archives': stats[0],
                    'active_archives': stats[1],
                    'deleted_archives': stats[2],
                    'total_tags': len(tag_counts),
                    'total_notes': sum(len(a['notes']) for a in data['archives'])
                }
            
            return json.dumps(data, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}", exc_info=True)
            return ""
    
    def export_to_markdown(self, include_deleted: bool = False) -> str:
        """
        Export all data to Markdown format
        
        Args:
            include_deleted: Include deleted archives
            
        Returns:
            Markdown string
        """
        try:
            md = StringIO()
            
            # Header
            md.write(f"# ArchiveBot 数据导出\n\n")
            md.write(f"**导出时间：** {format_datetime()}\n\n")
            md.write("---\n\n")
            
            # Export archives
            with self.db._lock:
                deleted_filter = "" if include_deleted else "WHERE deleted = 0"
                cursor = self.db.execute(f"""
                    SELECT 
                        id, title, content, content_type,
                        file_size, created_at, deleted
                    FROM archives
                    {deleted_filter}
                    ORDER BY created_at DESC
                """)
                
                archives = cursor.fetchall()
                md.write(f"## 📦 归档列表 ({len(archives)})\n\n")
                
                for row in archives:
                    archive_id = row[0]
                    title = row[1] or '无标题'
                    content = row[2] or ''
                    content_type = row[3]
                    file_size = row[4]
                    created_at = row[5]
                    deleted = row[6]
                    
                    # 通过tag_manager获取标签
                    tags = self.tag_manager.get_archive_tags(archive_id) if self.tag_manager else []
                    
                    # Archive header
                    status = " 🗑️" if deleted else ""
                    md.write(f"### {title}{status}\n\n")
                    md.write(f"**ID:** #{archive_id}  \n")
                    md.write(f"**类型:** {content_type}  \n")
                    md.write(f"**创建时间:** {created_at}  \n")
                    
                    if tags:
                        md.write(f"**标签:** {', '.join(f'`{tag}`' for tag in tags)}  \n")
                    
                    if file_size:
                        size_str = self._format_size(file_size)
                        md.write(f"**文件大小:** {size_str}  \n")
                    
                    md.write("\n")
                    
                    # Content
                    if content:
                        md.write(f"**内容:**\n\n```\n{content}\n```\n\n")
                    
                    # Notes
                    notes = self.note_manager.get_notes(archive_id)
                    if notes:
                        md.write(f"**📝 笔记 ({len(notes)}):**\n\n")
                        for note in notes:
                            md.write(f"- [{note['created_at']}] {note['content']}\n")
                        md.write("\n")
                    
                    md.write("---\n\n")
                
                # Tag statistics - 使用tag_manager获取
                tag_counts = {}
                if self.tag_manager:
                    all_tags = self.tag_manager.get_all_tags(limit=1000)
                    tag_counts = {tag['tag_name']: tag['count'] for tag in all_tags}
                
                if tag_counts:
                    md.write(f"## 🏷️ 标签统计 ({len(tag_counts)})\n\n")
                    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
                    for tag, count in sorted_tags:
                        md.write(f"- `{tag}`: {count}\n")
                    md.write("\n")
            
            return md.getvalue()
            
        except Exception as e:
            logger.error(f"Error exporting to Markdown: {e}", exc_info=True)
            return ""
    
    def export_to_csv(self, include_deleted: bool = False) -> str:
        """
        Export archives to CSV format
        
        Args:
            include_deleted: Include deleted archives
            
        Returns:
            CSV string
        """
        try:
            csv_buffer = StringIO()
            writer = csv.writer(csv_buffer)
            
            # Write header
            writer.writerow([
                'ID', '标题', '内容', '类型', '标签',
                '文件大小', '创建时间',
                '是否删除', '删除时间', '笔记数量'
            ])
            
            # Export archives
            with self.db._lock:
                deleted_filter = "" if include_deleted else "WHERE deleted = 0"
                cursor = self.db.execute(f"""
                    SELECT 
                        id, title, content, content_type,
                        file_size, created_at,
                        deleted, deleted_at
                    FROM archives
                    {deleted_filter}
                    ORDER BY created_at DESC
                """)
                
                for row in cursor.fetchall():
                    archive_id = row[0]
                    notes = self.note_manager.get_notes(archive_id)
                    note_count = len(notes)
                    
                    # 通过 tag_manager 获取标签
                    tags = self.tag_manager.get_archive_tags(archive_id) if self.tag_manager else []
                    tags_str = ', '.join(tags)
                    
                    writer.writerow([
                        row[0],  # id
                        row[1] or '',  # title
                        (row[2] or '')[:100],  # content (truncated)
                        row[3],  # content_type
                        tags_str,  # tags
                        row[4] or 0,  # file_size
                        row[5],  # created_at
                        '是' if row[6] else '否',  # deleted
                        row[7] or '',  # deleted_at
                        note_count
                    ])
            
            return csv_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}", exc_info=True)
            return ""
    
    def export_archives_by_tag(self, tag: str, format: str = 'markdown') -> str:
        """
        Export archives with specific tag
        
        Args:
            tag: Tag name
            format: Export format (markdown, json, csv)
            
        Returns:
            Exported data string
        """
        try:
            with self.db._lock:
                # 使用 JOIN 查询有指定标签的归档
                cursor = self.db.execute("""
                    SELECT DISTINCT
                        a.id, a.title, a.content, a.content_type,
                        a.file_size, a.created_at
                    FROM archives a
                    INNER JOIN archive_tags at ON a.id = at.archive_id
                    INNER JOIN tags t ON at.tag_id = t.id
                    WHERE a.deleted = 0 AND t.tag_name = ?
                    ORDER BY a.created_at DESC
                """, (tag,))
                
                archives = cursor.fetchall()
                
                if format == 'json':
                    data = {
                        'tag': tag,
                        'export_date': format_datetime(),
                        'archives': []
                    }
                    
                    for row in archives:
                        archive_id = row[0]
                        notes = self.note_manager.get_notes(archive_id)
                        
                        # 获取该归档的所有标签
                        archive_tags = self.tag_manager.get_archive_tags(archive_id) if self.tag_manager else []
                        
                        data['archives'].append({
                            'id': archive_id,
                            'title': row[1],
                            'content': row[2],
                            'content_type': row[3],
                            'tags': archive_tags,
                            'file_size': row[4],
                            'created_at': row[5],
                            'notes': notes
                        })
                    
                    return json.dumps(data, ensure_ascii=False, indent=2)
                
                elif format == 'csv':
                    csv_buffer = StringIO()
                    writer = csv.writer(csv_buffer)
                    writer.writerow(['ID', '标题', '内容', '类型', '标签', '文件大小', '创建时间', '笔记数量'])
                    
                    for row in archives:
                        archive_id = row[0]
                        notes = self.note_manager.get_notes(archive_id)
                        
                        # 获取该归档的所有标签
                        archive_tags = self.tag_manager.get_archive_tags(archive_id) if self.tag_manager else []
                        tags_str = ', '.join(archive_tags)
                        
                        writer.writerow([
                            row[0], row[1] or '', (row[2] or '')[:100],
                            row[3], tags_str, row[4] or 0,
                            row[5], len(notes)
                        ])
                    
                    return csv_buffer.getvalue()
                
                else:  # markdown
                    md = StringIO()
                    md.write(f"# 标签: {tag}\n\n")
                    md.write(f"**导出时间：** {format_datetime()}\n")
                    md.write(f"**归档数量：** {len(archives)}\n\n")
                    md.write("---\n\n")
                    
                    for row in archives:
                        archive_id = row[0]
                        notes = self.note_manager.get_notes(archive_id)
                        
                        # 获取该归档的所有标签
                        archive_tags = self.tag_manager.get_archive_tags(archive_id) if self.tag_manager else []
                        
                        md.write(f"### {row[1] or '无标题'}\n\n")
                        md.write(f"**ID:** #{archive_id}  \n")
                        md.write(f"**类型:** {row[3]}  \n")
                        md.write(f"**标签:** {', '.join(f'`{t}`' for t in archive_tags)}  \n")
                        md.write(f"**创建时间:** {row[5]}  \n\n")
                        
                        if row[2]:
                            md.write(f"{row[2]}\n\n")
                        
                        if notes:
                            md.write(f"**笔记:**\n\n")
                            for note in notes:
                                md.write(f"- {note['content']}\n")
                            md.write("\n")
                        
                        md.write("---\n\n")
                    
                    return md.getvalue()
            
        except Exception as e:
            logger.error(f"Error exporting archives by tag: {e}", exc_info=True)
            return ""
    
    def _format_size(self, size: int) -> str:
        """Format file size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}TB"
