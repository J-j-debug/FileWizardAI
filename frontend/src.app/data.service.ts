import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';


@Injectable({
  providedIn: 'root'
})
export class DataService {

  private apiUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {
  }

  getFormattedFiles(params: any): Observable<any> {
    return this.http.get<any>(this.apiUrl + "/get_files", { params: params });
  }

  updateStructure(newStructureBody: any): Observable<any> {
    return this.http.post<any>(this.apiUrl + "/update_files", newStructureBody);
  }

  ragSearch(params: HttpParams): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/rag_search`, { params });
  }

  openFile(fileToOpen: any): Observable<any> {
    return this.http.post<any>(this.apiUrl + "/open_file", { file_path: fileToOpen });
  }

  getLLMProviders(): Promise<any> {
    return this.http.get<any>(this.apiUrl + "/llm_providers").toPromise();
  }

  getCurrentLLMConfig(): Promise<any> {
    return this.http.get<any>(this.apiUrl + "/current_llm_config").toPromise();
  }

  updateLLMConfig(configData: any): Promise<any> {
    return this.http.post<any>(this.apiUrl + "/llm_config", configData).toPromise();
  }

  indexFiles(data: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/index_files`, data);
  }

  // --- Notebooks API ---

  getNotebooks(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/notebooks`);
  }

  createNotebook(notebookData: { name: string, description: string }): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/notebooks`, notebookData);
  }

  updateNotebook(id: number, notebookData: { name: string, description: string }): Observable<any> {
    return this.http.put<any>(`${this.apiUrl}/notebooks/${id}`, notebookData);
  }

  deleteNotebook(id: number): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/notebooks/${id}`);
  }

  getNotebookFiles(notebookId: number): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/notebooks/${notebookId}/files`);
  }

  addFilesToNotebook(notebookId: number, file_paths: string[]): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/notebooks/${notebookId}/files`, { file_paths });
  }

  removeFilesFromNotebook(notebookId: number, file_paths: string[]): Observable<any> {
    // Note: HttpClient delete method can have a body
    const options = { body: { file_paths } };
    return this.http.delete<any>(`${this.apiUrl}/notebooks/${notebookId}/files`, options);
  }

  indexNotebookFiles(notebookId: number, file_paths: string[], use_advanced_indexing: boolean): Observable<any> {
    const payload = {
      file_paths,
      use_advanced_indexing
    };
    return this.http.post<any>(`${this.apiUrl}/notebooks/${notebookId}/index`, payload);
  }

  searchInNotebook(notebookId: number, params: HttpParams): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/notebooks/${notebookId}/search`, { params });
  }
}
